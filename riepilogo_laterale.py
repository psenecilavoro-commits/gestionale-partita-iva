"""Riepilogo visibile nella barra laterale, senza stime presentate come dati certi."""
from decimal import Decimal

import pandas as pd
import streamlit as st

from fatturato import NOTA_TEST, euro, leggi_fatturato

D = Decimal


def tabella_laterale(righe: list[dict], *, scenario: bool = False,
                    contiene_prove: bool = False) -> None:
    """Tabella statica a due colonne, senza altezza fissa o scorrimento interno."""
    st.subheader("Conto economico")
    # VOCE è l'indice con intestazione visibile: non si aggiunge una terza
    # colonna numerata e la tabella si espande per mostrare tutte le righe.
    dati = pd.DataFrame(
        [{"VOCE": r["VOCE"], "VALORE": r["VALORE"]} for r in righe],
        columns=["VOCE", "VALORE"],
    ).set_index("VOCE")
    st.table(dati)
    if scenario:
        st.caption("Simulazione, non netto disponibile né importi fiscali definitivi.")
    elif contiene_prove:
        st.caption("* Fatturato con dati di prova. Valori parziali; le voci non calcolate restano vuote.")
    else:
        st.caption("Valori registrati parziali; le voci non calcolate restano vuote.")


def mostra_base(client, anno: dict, slot) -> None:
    """Valori documentali presenti anche quando lo scenario non è configurato."""
    righe = []
    contiene_prove = False
    try:
        ricavi = leggi_fatturato(client, anno["id"])
        from registri import leggi_tutti
        costi = leggi_tutti(client, "costs", fiscal_year_id=anno["id"])
        fatturato = sum((D(str(r["amount"])) for r in ricavi), D("0"))
        spese = sum((D(str(r["gross_amount"])) for r in costi), D("0"))
        contiene_prove = any(r.get("notes") == NOTA_TEST for r in ricavi)
        righe = [
            {"VOCE": "Fatturato *" if contiene_prove else "Fatturato",
             "VALORE": euro(fatturato) if ricavi else "—"},
            {"VOCE": "Spese lorde", "VALORE": euro(spese) if costi else "—"},
            {"VOCE": "Netto fiscale", "VALORE": "Da verificare"},
        ]
    except Exception:
        righe = [
            {"VOCE": "Fatturato", "VALORE": "—"},
            {"VOCE": "Spese lorde", "VALORE": "—"},
            {"VOCE": "Netto fiscale", "VALORE": "Da verificare"},
        ]
    with slot.container():
        tabella_laterale(righe, contiene_prove=contiene_prove)
