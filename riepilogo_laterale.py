"""Riepilogo visibile nella barra laterale, senza stime presentate come dati certi."""
from decimal import Decimal

import streamlit as st

from fatturato import NOTA_TEST, euro, leggi_fatturato

D = Decimal


def tabella_laterale(righe: list[dict], *, scenario: bool = False) -> None:
    """Mostra esclusivamente VOCE e VALORE; nessun dato è salvato o modificato."""
    st.subheader("Conto economico")
    st.dataframe(
        [{"VOCE": r["VOCE"], "VALORE": r["VALORE"]} for r in righe],
        hide_index=True,
        width="stretch",
        height=min(590, max(150, 34 * (len(righe) + 1))),
        column_config={
            "VOCE": st.column_config.TextColumn("VOCE", width="large"),
            "VALORE": st.column_config.TextColumn("VALORE", width="medium"),
        },
    )
    st.caption("Simulazione, non netto disponibile né importi fiscali definitivi." if scenario
               else "Valori registrati parziali; le voci non calcolate restano vuote.")


def mostra_base(client, anno: dict, slot) -> None:
    """Valori documentali presenti anche quando lo scenario non è configurato."""
    righe = []
    try:
        ricavi = leggi_fatturato(client, anno["id"])
        from registri import leggi_tutti
        costi = leggi_tutti(client, "costs", fiscal_year_id=anno["id"])
        fatturato = sum((D(str(r["amount"])) for r in ricavi), D("0"))
        spese = sum((D(str(r["gross_amount"])) for r in costi), D("0"))
        if any(r.get("notes") == NOTA_TEST for r in ricavi):
            stima = "Fatturato registrato (contiene prove)"
        else:
            stima = "Fatturato registrato"
        righe = [
            {"VOCE": stima, "VALORE": euro(fatturato) if ricavi else "—"},
            {"VOCE": "Spese registrate (importo lordo)",
             "VALORE": euro(spese) if costi else "—"},
            {"VOCE": "Netto fiscale", "VALORE": "Da verificare"},
        ]
    except Exception:
        righe = [
            {"VOCE": "Fatturato registrato", "VALORE": "—"},
            {"VOCE": "Spese registrate", "VALORE": "—"},
            {"VOCE": "Netto fiscale", "VALORE": "Da verificare"},
        ]
    with slot.container():
        tabella_laterale(righe)
