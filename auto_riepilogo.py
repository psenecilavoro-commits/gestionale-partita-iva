"""Vista unica mensile dell'auto; legge soltanto i registri già esistenti.

Il limite chilometrico è annuale: compare nel riepilogo annuo, non viene
ripetuto sui singoli mesi. Nessuna modifica a dati o formule fiscali.
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _chilometri, _formato_km, _veicoli, auto_unica
from auto_limiti import _leggi_impostazioni, mostra_limiti_auto
from auto_carburante import _euro
from fatturato import MESI
from registri import leggi_tutti

D = Decimal
CATEGORIE_AUTO = ("carburante", "autostrada", "rate_auto")
COLONNE = ("Mese", "Percorrenza", "Carburante", "Autostrada", "Rate auto",
           "Limite km", "Penale")


def _mese_spesa(spesa: dict) -> int:
    mese = int(str(spesa["expense_date"])[5:7])
    if not 1 <= mese <= 12:
        raise ValueError("Mese della spesa auto non valido.")
    return mese


def costruisci_tabella_auto(chilometri: list[dict], spese: list[dict],
                            categorie: list[dict], impostazioni: dict | None) -> list[dict]:
    """Dodici mesi e due righe di riepilogo, senza duplicare spese o limiti.

    Lo zero di un mese compilato è distinto dal mese non ancora compilato.
    Le spese multiple nello stesso mese contribuiscono una volta alla media.
    """
    km_mesi = {}
    for riga in chilometri:
        mese = int(riga["month"])
        if not 1 <= mese <= 12 or mese in km_mesi:
            raise ValueError("Percorrenza mensile non valida o duplicata.")
        km_mesi[mese] = D(str(riga["distance_km"]))

    codici = {riga["id"]: riga["code"] for riga in categorie
              if riga.get("code") in CATEGORIE_AUTO}
    importi = {codice: defaultdict(lambda: D("0")) for codice in CATEGORIE_AUTO}
    for riga in spese:
        codice = codici.get(riga["category_id"])
        if codice is not None:
            importi[codice][_mese_spesa(riga)] += D(str(riga["gross_amount"]))

    campi = (("carburante", "Carburante"), ("autostrada", "Autostrada"),
             ("rate_auto", "Rate auto"))
    righe = []
    for mese in range(1, 13):
        riga = {"Mese": MESI[mese - 1],
                "Percorrenza": _formato_km(km_mesi[mese]) if mese in km_mesi else "—"}
        for codice, etichetta in campi:
            riga[etichetta] = _euro(importi[codice][mese]) if mese in importi[codice] else "—"
        riga["Limite km"] = "—"
        riga["Penale"] = "—"
        righe.append(riga)

    km_totali = sum(km_mesi.values(), D("0"))
    limite = tariffa = None
    if impostazioni is not None and (impostazioni.get("annual_km_limit") is not None
                                    and impostazioni.get("excess_km_penalty") is not None):
        limite = D(str(impostazioni["annual_km_limit"]))
        tariffa = D(str(impostazioni["excess_km_penalty"]))

    def penale(km):
        if km is None or limite is None or tariffa is None:
            return "—"
        importo = max(km - limite, D("0")) * tariffa
        return _euro(importo.quantize(D("0.01"), rounding=ROUND_HALF_UP))

    registrato = {"Mese": "Totale registrato",
                  "Percorrenza": _formato_km(km_totali) if km_mesi else "—",
                  "Limite km": "—", "Penale": penale(km_totali if km_mesi else None)}
    previsto_km = km_totali / len(km_mesi) * 12 if km_mesi else None
    previsto = {"Mese": "Stima annua",
                "Percorrenza": _formato_km(previsto_km) if previsto_km is not None else "—",
                "Limite km": _formato_km(limite) if limite is not None else "—",
                "Penale": penale(previsto_km)}
    for codice, etichetta in campi:
        mesi = importi[codice]
        registrato[etichetta] = _euro(sum(mesi.values(), D("0"))) if mesi else "—"
        previsto[etichetta] = _euro(sum(mesi.values(), D("0")) / len(mesi) * 12) if mesi else "—"
    righe.extend([registrato, previsto])
    return [{colonna: riga[colonna] for colonna in COLONNE} for riga in righe]


def mostra_riepilogo_auto(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Riepilogo Auto")
    try:
        veicolo = auto_unica(_veicoli(client))
        veicolo_id = veicolo["id"] if veicolo else None
        chilometri = _chilometri(client, anno["id"], veicolo_id) if veicolo_id else []
        spese = (leggi_tutti(client, "costs", fiscal_year_id=anno["id"],
                            vehicle_id=veicolo_id) if veicolo_id else [])
        categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])
        impostazioni = (_leggi_impostazioni(client, anno["id"], veicolo_id)
                        if veicolo_id else None)
        tabella = costruisci_tabella_auto(chilometri, spese, categorie, impostazioni)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere il riepilogo Auto. Nessun dato modificato.")
        return

    if ((veicolo and veicolo.get("notes") == NOTA_VEICOLO_TEST)
            or any(str(r.get("notes") or "").startswith("DATI DI PROVA")
                   for r in [*chilometri, *spese])
            or (impostazioni and str(impostazioni.get("notes") or "").startswith("DATI DI PROVA"))):
        st.warning("Sono presenti dati di prova: non rappresentano percorrenze o spese effettive.")
    st.table(tabella)
    st.caption("Le spese dello stesso mese vengono sommate. Stima annua = totale dei mesi "
               "compilati ÷ numero di mesi compilati × 12. Il limite è annuale; "
               "la penale è calcolata solo se limite e tariffa sono disponibili.")
    if impostazioni and impostazioni.get("excess_km_penalty") is not None:
        st.caption("Tariffa della penale: " + _euro(D(str(impostazioni["excess_km_penalty"])))
                   + " per km eccedente.")
    # Mantieni accessibili i comandi dimostrativi preesistenti senza un altro
    # prospetto visibile nella schermata principale.
    if veicolo and veicolo.get("notes") == NOTA_VEICOLO_TEST:
        with st.expander("Gestisci limite e penale di prova"):
            mostra_limiti_auto(client, anno)
