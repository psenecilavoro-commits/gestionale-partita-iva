"""Riepilogo del Conto economico nella barra laterale."""

from decimal import Decimal as D, ROUND_HALF_UP

import pandas as pd
import streamlit as st

from fatturato import CENT, euro


def _fmt(v: D) -> str:
    return euro(v.quantize(CENT, rounding=ROUND_HALF_UP))


def tabella_laterale(righe: list[dict]) -> None:
    """Tabella compatta a due colonne con i valori chiave del Conto economico."""
    st.subheader("Conto economico")
    dati = pd.DataFrame(
        [{"VOCE": r["VOCE"], "VALORE": r["VALORE"]} for r in righe],
        columns=["VOCE", "VALORE"],
    ).set_index("VOCE")
    st.table(dati)
    st.caption("Valori ripresi dal Conto economico dell'anno selezionato.")


def _vuota() -> list[dict]:
    return [
        {"VOCE": "Fatturato", "VALORE": "—"},
        {"VOCE": "Costi annui", "VALORE": "—"},
        {"VOCE": "Netto annuo stimato", "VALORE": "—"},
        {"VOCE": "Netto/12 medio", "VALORE": "—"},
        {"VOCE": "Netto/12 senza costi", "VALORE": "—"},
    ]


def mostra_base(client, anno: dict, slot) -> None:
    """Mostra gli stessi valori calcolati nella scheda Conto economico."""
    try:
        if int(anno["fiscal_year"]) == 2026:
            from forfettario_2026 import valori_conto_2026
            valori = valori_conto_2026(client, anno)
            righe = [
                {"VOCE": "Fatturato", "VALORE": _fmt(valori["fatturato_stimato"])},
                {"VOCE": "Costi annui", "VALORE": _fmt(valori["costi_annui"])},
                {"VOCE": "Netto annuo stimato", "VALORE": _fmt(valori["netto"])},
                {"VOCE": "Netto/12 medio", "VALORE": _fmt(valori["netto_mese"])},
                {"VOCE": "Netto/12 senza costi", "VALORE": _fmt(valori["netto_no_costi_mese"])},
            ]
        else:
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
            righe = [
                {"VOCE": "Fatturato", "VALORE": _fmt(valori["B1"])},
                {"VOCE": "Costi annui", "VALORE": _fmt(valori["B13"])},
                {"VOCE": "Netto annuo stimato", "VALORE": _fmt(valori["B18"])},
                {"VOCE": "Netto/12 medio", "VALORE": _fmt(valori["B19"])},
                {"VOCE": "Netto/12 senza costi", "VALORE": _fmt(valori["B22"])},
            ]
    except Exception:
        righe = _vuota()

    with slot.container():
        tabella_laterale(righe)
