"""Ripartizione del fabbisogno fiscale residuo sugli accantonamenti mensili.

La funzione riusa esclusivamente i calcoli già validati del gestionale:
- 2026: modello forfettario dedicato;
- dal 2027: Conto economico ordinario.

Non scrive nulla su Supabase: mostra quanto resta da accantonare e lo divide
automaticamente tra i mesi ancora privi di un accantonamento registrato.
"""
from decimal import Decimal as D, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from accantonamenti import leggi_accantonamenti
from fatturato import CENT, MESI, euro


def obiettivo_annuo_foglio(fatturato: D, inps: D, irpef: D,
                           veneto: D, verona: D, avanzo_ap: D = D("0")) -> D:
    """Mantiene disponibile la formula storica usata nei test del foglio."""
    valori = (fatturato, inps, irpef, veneto, verona, avanzo_ap)
    if any(not n.is_finite() or n < 0 for n in valori):
        raise ValueError("Importi del confronto non validi")
    return inps + irpef + veneto + verona - fatturato * D("0.115") - avanzo_ap


def quota_mesi_vuoti_foglio(obiettivo: D, gia_accantonato: D,
                            mesi_compilati: int) -> D | None:
    """Distribuisce il residuo su 12 meno i mesi già compilati."""
    if (not obiettivo.is_finite() or not gia_accantonato.is_finite()
            or gia_accantonato < 0 or type(mesi_compilati) is not int
            or not 0 <= mesi_compilati <= 12):
        raise ValueError("Scenario accantonamenti non valido")
    if mesi_compilati == 0 and gia_accantonato != 0:
        raise ValueError("Non puoi indicare accantonamenti senza mesi compilati")
    if mesi_compilati == 12:
        return None
    return (obiettivo - gia_accantonato) / D(12 - mesi_compilati)


def ripartisci_residuo(obiettivo: D, gia_accantonato: D,
                       mesi_compilati: int) -> dict[str, D | int | None]:
    """Versione operativa: non propone mai una quota negativa da accantonare."""
    quota_grezza = quota_mesi_vuoti_foglio(obiettivo, gia_accantonato, mesi_compilati)
    differenza = obiettivo - gia_accantonato
    residuo = max(differenza, D("0"))
    eccedenza = max(-differenza, D("0"))
    restanti = 12 - mesi_compilati
    quota = None if quota_grezza is None else max(quota_grezza, D("0"))
    return {
        "residuo": residuo,
        "eccedenza": eccedenza,
        "mesi_restanti": restanti,
        "quota_mensile": quota,
    }


def _fmt(v: D) -> str:
    return euro(v.quantize(CENT, rounding=ROUND_HALF_UP))


def _mesi_accantonati(riserve: list[dict]) -> set[int]:
    mesi: set[int] = set()
    for riga in riserve:
        mese = int(riga["month"])
        if mese not in range(1, 13) or mese in mesi:
            raise ValueError("Mese accantonamento duplicato o non valido.")
        mesi.add(mese)
    return mesi


def _obiettivo_2026(client: Client, anno: dict) -> tuple[D, str]:
    from forfettario_2026 import valori_conto_2026

    valori = valori_conto_2026(client, anno)
    obiettivo = valori["inps_totale"] + valori["imposta_sostitutiva"]
    descrizione = (
        f"INPS previsto {_fmt(valori['inps_totale'])} + "
        f"imposta sostitutiva prevista {_fmt(valori['imposta_sostitutiva'])}"
    )
    return obiettivo, descrizione


def _obiettivo_ordinario(client: Client, anno: dict) -> tuple[D, str]:
    from conto_economico import (
        DEFAULT_CONTRIBUTI_AP,
        DEFAULT_FONDO_PENSIONE,
        valori_conto_corrente,
    )

    ap = D(str(st.session_state.get(
        f"conto_contributi_ap_{anno['id']}", DEFAULT_CONTRIBUTI_AP
    )))
    fondo = D(str(st.session_state.get(
        f"conto_fondo_pensione_{anno['id']}", DEFAULT_FONDO_PENSIONE
    )))
    valori = valori_conto_corrente(client, anno, ap, fondo)

    # Riprende la logica pratica già usata nel vecchio prospetto accantonamenti:
    # il fabbisogno da mettere da parte è INPS + imposte nette, al netto della
    # ritenuta d'acconto stimata all'11,5% del fatturato.
    ritenute = valori["B1"] * D("0.115")
    obiettivo = max(valori["B11"] + valori["IMPOSTE_NETTE"] - ritenute, D("0"))
    descrizione = (
        f"INPS previsto {_fmt(valori['B11'])} + imposte nette previste "
        f"{_fmt(valori['IMPOSTE_NETTE'])} − ritenute stimate {_fmt(ritenute)}"
    )
    return obiettivo, descrizione


def mostra_confronto_accantonamenti(client: Client, anno: dict) -> None:
    """Mostra il residuo reale da accantonare e la quota sui mesi ancora vuoti."""
    st.divider()
    st.subheader("Residuo da accantonare")
    st.caption(
        "Il calcolo usa gli stessi valori previsionali del Conto economico e gli "
        "accantonamenti già registrati. Non modifica automaticamente nessun mese."
    )

    try:
        riserve = leggi_accantonamenti(client, anno["id"])
        mesi_compilati = _mesi_accantonati(riserve)
        gia_accantonato = sum(
            (D(str(r["reserved_amount"])) for r in riserve), D("0")
        )
        if int(anno["fiscal_year"]) == 2026:
            obiettivo, descrizione = _obiettivo_2026(client, anno)
        else:
            obiettivo, descrizione = _obiettivo_ordinario(client, anno)
        ripartizione = ripartisci_residuo(
            obiettivo, gia_accantonato, len(mesi_compilati)
        )
    except ValueError as exc:
        st.info(str(exc))
        return
    except Exception:
        st.error("Impossibile calcolare il residuo degli accantonamenti.")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Fabbisogno fiscale annuo stimato", _fmt(obiettivo))
    c2.metric("Già accantonato", _fmt(gia_accantonato))
    c3.metric("Residuo da accantonare", _fmt(ripartizione["residuo"]))

    st.caption(f"Composizione del fabbisogno: {descrizione}.")

    mesi_vuoti = [
        nome for numero, nome in enumerate(MESI, start=1)
        if numero not in mesi_compilati
    ]
    quota = ripartizione["quota_mensile"]

    if ripartizione["mesi_restanti"] == 0:
        st.info("Tutti i 12 mesi hanno già un accantonamento registrato.")
    elif ripartizione["residuo"] == 0:
        st.success(
            "Il fabbisogno fiscale stimato risulta già coperto dagli accantonamenti "
            "registrati: al momento non occorre aumentare la quota dei mesi successivi."
        )
        if ripartizione["eccedenza"] > 0:
            st.metric("Eccedenza rispetto al fabbisogno stimato",
                      _fmt(ripartizione["eccedenza"]))
    else:
        st.metric(
            f"Quota indicativa per ciascuno dei {ripartizione['mesi_restanti']} mesi restanti",
            _fmt(quota),
        )
        st.caption(
            f"{_fmt(ripartizione['residuo'])} / "
            f"{ripartizione['mesi_restanti']} mesi. "
            f"Mesi ancora senza accantonamento: {', '.join(mesi_vuoti)}."
        )

    st.caption(
        "È un riparto previsionale: se cambiano fatturato, costi, imposte o "
        "accantonamenti registrati, la quota viene ricalcolata automaticamente."
    )
