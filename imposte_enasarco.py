"""Confronto matematico Enasarco del foglio originale, NON contributi dovuti.

Fatturato!B19/E19/H19/K19 = MIN(stima annuale mandante,
Imposte!E1) * 0,085. Fatturato!B20/E20/H20/K20 verifica invece
il fatturato REGISTRATO rispetto al massimale (STOP se maggiore).
Non si detrae mai Enasarco dal fatturato letto dal database.
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
    """Restituisce risultati per mandante, totale NON arrotondato e presenza mono.

    Le formule del foglio usano il massimale plurimandatario per tutti e
    quattro gli esempi. Con mandanti mono non inventiamo una nuova formula.
    """
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
        # Anche per un mese ancora assente il monitor non è uno zero fittizio.
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
            "Massimale foglio": euro(massimale) if rapporto == "plurimandatario" else "—",
            "Enasarco stimato (separato)": euro(quota.quantize(CENT, rounding=ROUND_HALF_UP)) if quota is not None else "—",
            "Controllo massimale": stato,
        })
    return dettagli, totale, mono_da_chiarire


def mostra_confronto_enasarco(client: Client, anno: dict, presenti: dict) -> None:
    st.divider()
    st.subheader("Enasarco · confronto delle formule del foglio")
    st.caption(
        "Tre controlli: proiezione annuale per mandante; quota Enasarco mostrata A PARTE; "
        "VAI/STOP sul fatturato registrato. Nessuna sottrazione dal Fatturato."
    )
    if any(codice not in presenti for codice in RICHIESTI):
        st.info("Per il confronto carica prima aliquota e massimale plurimandatario nel blocco Enasarco.")
        return
    try:
        aliquota = Decimal(str(presenti["enasarco_tasso_foglio"]["value"]))
        massimale = Decimal(str(presenti["enasarco_massimale_pluri"]["value"]))
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        righe, totale, mono = calcola_confronto(mandanti, ricavi, aliquota, massimale)
    except Exception:
        st.error("Confronto Enasarco non disponibile. Nessun dato modificato.")
        return
    if not righe:
        st.info("Inserisci prima una mandante in Fatturato.")
        return
    if any(r.get("notes") == NOTA_TEST for r in ricavi):
        st.warning("DATI DI PROVA: non sono versamenti o contributi realmente dovuti.")
    st.dataframe(righe, hide_index=True, width="stretch")
    if mono:
        st.info("Sono presenti mandanti monomandatarie: il foglio usa il massimale plurimandatario. "
                "La relativa formula resta sospesa finché non la concordiamo.")
    elif all(r["Enasarco stimato (separato)"] != "—" for r in righe):
        st.metric("Enasarco annuo stimato · separato dal fatturato",
                  euro(totale.quantize(CENT, rounding=ROUND_HALF_UP)))
    else:
        st.info("Totale non mostrato: alcune mandanti non hanno ancora mesi compilati.")
    if aliquota == Decimal("0.085") and massimale == Decimal("30057"):
        st.caption("Riferimenti: Fatturato!B17/K17 (stime), B19/E19/H19/K19 "
                   "(Enasarco) e B20/E20/H20/K20 (VAI/STOP). "
                   "Con i quattro esempi del foglio il totale è 5.206,85 €.")
    else:
        st.caption("Parametri modificati rispetto al foglio: importi ricalcolati "
                   "con i valori configurati, sempre provvisori.")
    st.warning("Questo è soltanto un confronto di formule: nessun importo viene registrato "
               "come Enasarco versato, nessun calcolo del netto mensile è attivato.")
