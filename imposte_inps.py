"""Confronto INPS in sola lettura delle formule del foglio originale.

Non calcola versamenti effettivi, imposte definitive o il netto mensile.
Non sottrae mai l'Enasarco dal fatturato; lo considera separatamente
SOLO nella formula di confronto dell'imponibile INPS del foglio.
"""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from costi_tabella import _penale
from fatturato import NOTA_TEST, euro, leggi_fatturato, riepilogo
from imposte_enasarco import calcola_confronto
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI as VOCI_TEST_COSTI, calcola_riepilogo

D = Decimal
CENT = D("0.01")
PARAMETRI = (
    "enasarco_tasso_foglio", "enasarco_massimale_pluri",
    "inps_fisso_foglio", "inps_minimale_foglio", "inps_aliquota_prima_foglio",
    "inps_soglia_seconda_foglio", "inps_aliquota_seconda_foglio",
    "inps_massimale_foglio",
)


def calcola_inps_foglio(fatturato: D, costi_deducibili: D, enasarco: D,
                        fisso: D, minimale: D, prima: D, soglia: D,
                        seconda: D, massimale: D) -> tuple[D, D, D]:
    """Conto economico!B8 e Imposte!B6/B5, senza arrotondamenti intermedi."""
    valori = (fatturato, costi_deducibili, enasarco, fisso, minimale,
              prima, soglia, seconda, massimale)
    if any(not valore.is_finite() or valore < 0 for valore in valori):
        raise ValueError("I valori del confronto devono essere finiti e non negativi")
    if not (minimale <= soglia <= massimale) or prima > 1 or seconda > 1:
        raise ValueError("Soglie o aliquote INPS non coerenti: chiarire i parametri")
    imponibile = fatturato - costi_deducibili - enasarco
    # Formula del foglio Imposte!B6, trascritta senza arrotondamenti intermedi.
    if imponibile <= minimale:
        eccedente = D("0")
    else:
        imponibile_limitato = min(imponibile, massimale)
        if imponibile_limitato <= soglia:
            eccedente = (imponibile_limitato - minimale) * prima
        else:
            eccedente = ((soglia - minimale) * prima
                         + (imponibile_limitato - soglia) * seconda)
    return imponibile, eccedente, fisso + eccedente


def _nessun_altro_costo(client: Client, anno_id: str) -> bool:
    """Non presentare il totale di sette voci come completo se esistono altre spese."""
    categorie = (client.table("cost_categories")
                 .select("id,code").eq("fiscal_year_id", anno_id).execute()).data or []
    esterne = {c["id"] for c in categorie if c["code"] not in VOCI_TEST_COSTI}
    if not esterne:
        return True
    stime = (client.table("annual_cost_estimates")
             .select("category_id,estimated_gross_amount")
             .eq("fiscal_year_id", anno_id).execute()).data or []
    spese = (client.table("costs").select("category_id,gross_amount")
             .eq("fiscal_year_id", anno_id).execute()).data or []
    return not any(r["category_id"] in esterne and D(str(r[campo])) != 0
                   for gruppo, campo in ((stime, "estimated_gross_amount"),
                                         (spese, "gross_amount")) for r in gruppo)


def mostra_confronto_inps(client: Client, anno: dict, presenti: dict) -> None:
    st.divider()
    st.subheader("INPS · confronto delle formule del foglio")
    st.caption("Tre passaggi: imponibile di confronto, quota eccedente e totale con INPS fisso. "
               "L'Enasarco resta una voce separata dal fatturato.")
    mancanti = [chiave for chiave in PARAMETRI if chiave not in presenti]
    if mancanti:
        st.info("Carica prima tutti i parametri Enasarco e INPS per visualizzare il confronto.")
        return
    try:
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        if not mandanti or not ricavi:
            st.info("Per il confronto servono le provvigioni di prova nella scheda Fatturato.")
            return
        if any(r.get("notes") != NOTA_TEST for r in ricavi):
            st.info("Il confronto dei sette costi di prova è sospeso: non mescolo ricavi ordinari e dati di prova.")
            return
        dati_mandanti, _registrato, fatturato = riepilogo(mandanti, ricavi)
        if fatturato is None or any(dato["mesi"] == 0 for dato in dati_mandanti):
            st.info("Occorre almeno un mese compilato per ciascuna mandante.")
            return
        _dettagli, enasarco, mono = calcola_confronto(
            mandanti, ricavi,
            D(str(presenti["enasarco_tasso_foglio"]["value"])),
            D(str(presenti["enasarco_massimale_pluri"]["value"])),
        )
        if mono:
            st.info("È presente una mandante monomandataria: concordiamo la formula prima di proseguire.")
            return
        costi, mancanti_costi, non_test = calcola_riepilogo(client, anno["id"])
        if non_test or mancanti_costi or len(costi) != len(VOCI_TEST_COSTI):
            st.info("Il confronto richiede tutte e sette le voci Costi di prova, senza modifiche o voci mancanti.")
            return
        if not _nessun_altro_costo(client, anno["id"]):
            st.info("Sono presenti altre spese oltre alle sette voci di prova: il confronto completo è sospeso.")
            return
        impostazioni = (client.table("vehicle_year_settings")
                        .select("vehicle_id,annual_km_limit,excess_km_penalty")
                        .eq("fiscal_year_id", anno["id"]).execute()).data or []
        km = (client.table("vehicle_monthly")
              .select("vehicle_id,month,distance_km")
              .eq("fiscal_year_id", anno["id"]).execute()).data or []
        penale = _penale(impostazioni, km)
        if penale is not None and penale != 0:
            st.info("La penale chilometrica stimata non è zero: occorre includerla nei costi prima del confronto INPS.")
            return
        deducibili = sum((r["Deducibile"] for r in costi), D("0"))
        p = {codice: D(str(presenti[codice]["value"])) for codice in PARAMETRI}
        imponibile, eccedente, totale = calcola_inps_foglio(
            fatturato, deducibili, enasarco,
            p["inps_fisso_foglio"], p["inps_minimale_foglio"],
            p["inps_aliquota_prima_foglio"], p["inps_soglia_seconda_foglio"],
            p["inps_aliquota_seconda_foglio"], p["inps_massimale_foglio"],
        )
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere il confronto INPS: nessun dato modificato.")
        return

    st.warning("CONFRONTO DI PROVA: valori e aliquote del foglio non verificati per il 2027. "
               "Non sono importi da versare e non modificano il fatturato.")
    st.dataframe([
        {"Passaggio": "Fatturato annuo stimato (invariato)", "Importo": euro(fatturato.quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Fatturato!B41"},
        {"Passaggio": "Costi deducibili stimati", "Importo": euro(deducibili.quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Costi!F14"},
        {"Passaggio": "Enasarco stimato (separato)", "Importo": euro(enasarco.quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Imposte!E4"},
        {"Passaggio": "1 · Imponibile INPS del foglio", "Importo": euro(imponibile.quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Conto economico!B8"},
        {"Passaggio": "2 · INPS eccedente del foglio", "Importo": euro(eccedente.quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Imposte!B6"},
        {"Passaggio": "INPS fisso del foglio", "Importo": euro(p["inps_fisso_foglio"].quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Imposte!B5"},
        {"Passaggio": "3 · INPS complessivo del foglio", "Importo": euro(totale.quantize(CENT, rounding=ROUND_HALF_UP)), "Foglio": "Conto economico!B10"},
    ], hide_index=True, width="stretch")
    st.caption("L'Enasarco NON riduce il fatturato registrato: è sottratto soltanto nella specifica "
               "formula dell'imponibile INPS, esattamente come nel foglio. Nessun doppio conteggio.")
    if all(p[k] == v for k, v in (
        ("enasarco_tasso_foglio", D("0.085")),
        ("enasarco_massimale_pluri", D("30057")),
        ("inps_fisso_foglio", D("4611.64")),
        ("inps_minimale_foglio", D("18808.01")),
        ("inps_aliquota_prima_foglio", D("0.2448")),
        ("inps_soglia_seconda_foglio", D("56224")),
        ("inps_aliquota_seconda_foglio", D("0.2548")),
        ("inps_massimale_foglio", D("122295")),
    )):
        attesi = (D("99945.20"), D("20299.60"), D("24911.24"))
        ottenuti = (imponibile, eccedente, totale)
        if all(a.quantize(CENT, rounding=ROUND_HALF_UP) == b
               for a, b in zip(ottenuti, attesi)):
            st.success("I tre risultati riproducono i valori di prova del foglio originale.")
        else:
            st.warning("I tre risultati non coincidono con il foglio di prova: controlla le voci a monte.")
    st.caption("Il massimale INPS 122.295 € è provvisorio nel foglio (2026), non confermato per il 2027. "
               "Il netto mensile e i contributi effettivamente pagati restano da sviluppare.")
