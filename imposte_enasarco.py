"""Scenario matematico Enasarco, NON contributi realmente dovuti.

La quota di scenario e' separata dal fatturato registrato, che non va
ridotto automaticamente dell'Enasarco. I massimali vanno confermati.
"""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import euro, leggi_fatturato, riepilogo, NOTA_TEST
from mandanti import elenco_mandanti

CENT = Decimal("0.01")
RICHIESTI = ("enasarco_tasso_foglio", "enasarco_massimale_pluri")


def calcola_confronto(mandanti: list[dict], ricavi: list[dict], aliquota: Decimal,
                      massimale: Decimal) -> tuple[list[dict], Decimal, bool]:
    """Risultati per mandante, totale non arrotondato e presenza mono."""
    if any(not x.is_finite() or x < 0 for x in (aliquota, massimale)):
        raise ValueError("Parametro Enasarco non valido")
    risultati, _totale_registrato, _stima = riepilogo(mandanti, ricavi)
    dettagli = []
    totale = Decimal("0")
    mono_da_chiarire = False
    for mandante, risultato in zip(mandanti, risultati):
        registrato = risultato["totale"]
        previsione = risultato["stima"]
        rapporto = mandante.get("enasarco_relationship")
        if previsione is None:
            quota, stato = None, "—"
        elif rapporto != "plurimandatario":
            quota, stato = None, "Da concordare (mono)"
            mono_da_chiarire = True
        else:
            quota = min(previsione, massimale) * aliquota
            totale += quota
            stato = "STOP" if registrato > massimale else "VAI"
        dettagli.append({
            "Mandante": mandante["name"],
            "Provvigioni registrate": euro(registrato) if risultato["mesi"] else "—",
            "Stima annuale": euro(previsione.quantize(CENT, rounding=ROUND_HALF_UP)) if previsione is not None else "—",
            "Massimale di scenario": euro(massimale) if rapporto == "plurimandatario" else "—",
            "Enasarco stimato (separato)": euro(quota.quantize(CENT, rounding=ROUND_HALF_UP)) if quota is not None else "—",
            "Controllo massimale": stato,
        })
    return dettagli, totale, mono_da_chiarire


def mostra_confronto_enasarco(client: Client, anno: dict, presenti: dict) -> None:
    st.divider()
    st.subheader("Enasarco · scenario")
    st.caption("Proiezione annuale per mandante, quota Enasarco separata e controllo "
               "VAI/STOP sul fatturato registrato. Nessuna sottrazione dal Fatturato.")
    if any(codice not in presenti for codice in RICHIESTI):
        st.info("Carica prima aliquota e massimale plurimandatario nel blocco Enasarco.")
        return
    try:
        aliquota = Decimal(str(presenti["enasarco_tasso_foglio"]["value"]))
        massimale = Decimal(str(presenti["enasarco_massimale_pluri"]["value"]))
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        righe, totale, mono = calcola_confronto(mandanti, ricavi, aliquota, massimale)
    except Exception:
        st.error("Scenario Enasarco non disponibile. Nessun dato modificato.")
        return
    if not righe:
        st.info("Inserisci prima una mandante in Fatturato.")
        return
    if any(r.get("notes") == NOTA_TEST for r in ricavi):
        st.warning("DATI DI PROVA: non sono versamenti o contributi realmente dovuti.")
    st.dataframe(righe, hide_index=True, width="stretch")
    if mono:
        st.info("Sono presenti mandanti monomandatarie: questo scenario utilizza "
                "solo il massimale plurimandatario. Il calcolo mono resta sospeso.")
    elif all(r["Enasarco stimato (separato)"] != "—" for r in righe):
        st.metric("Enasarco annuo stimato · separato dal fatturato",
                  euro(totale.quantize(CENT, rounding=ROUND_HALF_UP)))
    else:
        st.info("Totale non mostrato: alcune mandanti non hanno ancora mesi compilati.")
    if aliquota == Decimal("0.085") and massimale == Decimal("30057"):
        st.caption("Con i quattro esempi dimostrativi il totale è 5.206,85 €. "
                   "Aliquota e massimale sono parametri da verificare.")
    else:
        st.caption("Importi ricalcolati con i parametri configurati, ancora provvisori.")
    st.warning("Nessun importo viene registrato come Enasarco versato; "
               "questo scenario non determina un netto mensile.")
