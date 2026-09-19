"""Primo confronto costi: riga Commercialista del foglio originale.

Solo simulazione con dati TEST espliciti. Stime annuali separate dai costi
realmente sostenuti; aliquote usate qui sono quelle del foglio di prova,
NON una conferma del trattamento fiscale applicabile nel 2027.
"""

from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import euro

CODICE = "commercialista"
NOTA_TEST = "DATI DI PROVA - costo Commercialista dal foglio originale"
CENT = Decimal("0.01")


def _euro_arrotondato(importo: Decimal) -> str:
    return euro(importo.quantize(CENT, rounding=ROUND_HALF_UP))


def _leggi_categoria(client: Client, anno_id: str) -> dict | None:
    risposta = (
        client.table("cost_categories")
        .select("id,name,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,notes")
        .eq("fiscal_year_id", anno_id)
        .eq("code", CODICE)
        .limit(1)
        .execute()
    )
    return risposta.data[0] if risposta.data else None


def _leggi_stima(client: Client, anno_id: str, categoria_id: str) -> dict | None:
    risposta = (
        client.table("annual_cost_estimates")
        .select("id,estimated_gross_amount,amount_includes_vat,notes")
        .eq("fiscal_year_id", anno_id)
        .eq("category_id", categoria_id)
        .limit(1)
        .execute()
    )
    return risposta.data[0] if risposta.data else None


def _crea_prova(client: Client, anno_id: str) -> None:
    """Ripetibile anche se il primo inserimento ha creato solo la categoria."""
    categoria = _leggi_categoria(client, anno_id)
    if categoria is None:
        risposta = client.table("cost_categories").insert({
            "fiscal_year_id": anno_id,
            "code": CODICE,
            "name": "Commercialista",
            "vat_rate": "0.22",
            "vat_deductible_rate": "1",
            "cost_deductible_rate": "1",
            "notes": "Parametri di confronto dal foglio; verificare prima dell'uso reale.",
        }).execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Creazione categoria non confermata")
        categoria = risposta.data[0]
    elif categoria.get("notes") != "Parametri di confronto dal foglio; verificare prima dell'uso reale.":
        raise ValueError("Categoria Commercialista già configurata: non sovrascrivo le sue impostazioni.")

    if _leggi_stima(client, anno_id, categoria["id"]) is not None:
        raise ValueError("È già presente un costo Commercialista: non lo sovrascrivo.")
    risposta = client.table("annual_cost_estimates").insert({
        "fiscal_year_id": anno_id,
        "category_id": categoria["id"],
        "estimated_gross_amount": "3000.00",
        "amount_includes_vat": True,
        "notes": NOTA_TEST,
    }).execute()
    if len(risposta.data or []) != 1:
        raise RuntimeError("Creazione stima non confermata")


def _elimina_stima_test(client: Client, anno_id: str, stima: dict) -> None:
    if stima.get("notes") != NOTA_TEST:
        raise ValueError("Eliminazione consentita qui solo per il dato di prova originale.")
    risposta = (
        client.table("annual_cost_estimates")
        .delete()
        .eq("id", stima["id"])
        .eq("fiscal_year_id", anno_id)
        .eq("notes", NOTA_TEST)
        .execute()
    )
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata")


def _calcola(gross: Decimal, categoria: dict, include_iva: bool) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    aliquota = Decimal(str(categoria["vat_rate"]))
    percentuale_iva = Decimal(str(categoria["vat_deductible_rate"]))
    percentuale_costo = Decimal(str(categoria["cost_deductible_rate"]))
    iva = gross * aliquota / (Decimal("1") + aliquota) if include_iva else Decimal("0")
    iva_detraibile = iva * percentuale_iva
    # L'IVA non detraibile resta parte del costo. L'importo è lordo e IVA inclusa.
    costo_effettivo = gross - iva_detraibile
    deducibile = costo_effettivo * percentuale_costo
    limite = categoria.get("deductible_limit")
    if limite is not None:
        deducibile = min(deducibile, Decimal(str(limite)))
    return iva, iva_detraibile, costo_effettivo, deducibile


def mostra_costi(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Costi · confronto iniziale")
    st.caption("Primo esempio: Commercialista. La stima annuale è separata dalle spese effettive.")
    try:
        categoria = _leggi_categoria(client, anno["id"])
        stima = _leggi_stima(client, anno["id"], categoria["id"]) if categoria else None
    except Exception:
        st.error("Impossibile leggere i costi: nessun dato modificato.")
        return

    if stima is None:
        st.info("Non è ancora presente il costo annuale Commercialista.")
        if anno["status"] == "open":
            st.caption("Dati del foglio di prova: 3.000 € IVA inclusa; IVA 22%; IVA detraibile 100%; costo deducibile 100%. Parametri di test da verificare prima dell'uso reale.")
            if st.button("Carica costo di prova Commercialista"):
                try:
                    _crea_prova(client, anno["id"])
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("Caricamento non confermato. Aggiorna la pagina e verifica la sezione prima di riprovare.")
                else:
                    st.rerun()
        return

    lordo = Decimal(str(stima["estimated_gross_amount"]))
    iva, iva_detraibile, costo, deducibile = _calcola(lordo, categoria, bool(stima["amount_includes_vat"]))
    if stima.get("notes") == NOTA_TEST:
        st.warning("DATI DI PROVA: costo Commercialista, non rappresenta una spesa reale.")
    st.dataframe([{
        "Categoria": categoria["name"],
        "Totale IVA compresa": _euro_arrotondato(lordo),
        "IVA scorporata": _euro_arrotondato(iva),
        "IVA detraibile": _euro_arrotondato(iva_detraibile),
        "Costo al netto dell'IVA detraibile": _euro_arrotondato(costo),
        "Costo deducibile": _euro_arrotondato(deducibile),
    }], hide_index=True, use_container_width=True)
    st.caption("Confronto con la riga Commercialista del foglio: IVA 540,98 €; netto e deducibile 2.459,02 €. Le aliquote sono quelle del foglio, non parametri fiscali definitivi per il 2027.")

    if anno["status"] == "open" and stima.get("notes") == NOTA_TEST:
        with st.expander("Elimina il costo di prova Commercialista"):
            conferma = st.checkbox("Confermo che voglio eliminare il costo di prova")
            if st.button("Elimina costo di prova", disabled=not conferma):
                try:
                    _elimina_stima_test(client, anno["id"], stima)
                except Exception:
                    st.error("Eliminazione non confermata. Controlla la sezione prima di riprovare.")
                else:
                    st.rerun()
