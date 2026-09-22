"""Scenario INPS in sola lettura, non versamenti effettivi o netto mensile.

Il fatturato registrato resta integrale; la voce Enasarco e' separata.
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
    """Formula di scenario senza arrotondamenti intermedi."""
    valori = (fatturato, costi_deducibili, enasarco, fisso, minimale,
              prima, soglia, seconda, massimale)
    if any(not valore.is_finite() or valore < 0 for valore in valori):
        raise ValueError("I valori del confronto devono essere finiti e non negativi")
    if not (minimale <= soglia <= massimale) or prima > 1 or seconda > 1:
        raise ValueError("Soglie o aliquote INPS non coerenti: chiarire i parametri")
    imponibile = fatturato - costi_deducibili - enasarco
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
    """Evita di presentare un prospetto incompleto come totale complessivo."""
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
    st.subheader("INPS · scenario")
    st.caption("Imponibile ipotetico, quota eccedente e totale con INPS fisso. "
               "Enasarco e fatturato restano voci distinte.")
    if any(chiave not in presenti for chiave in PARAMETRI):
        st.info("Carica prima i parametri Enasarco e INPS per visualizzare lo scenario.")
        return
    try:
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        if not mandanti or not ricavi:
            st.info("Sono necessari i dati di prova nella scheda Fatturato.")
            return
        if any(r.get("notes") != NOTA_TEST for r in ricavi):
            st.info("Scenario sospeso: non vengono mescolati ricavi ordinari e dati di prova.")
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
            st.info("È presente una mandante monomandataria: serve una formula specifica.")
            return
        costi, mancanti_costi, non_test = calcola_riepilogo(client, anno["id"])
        if non_test or mancanti_costi or len(costi) != len(VOCI_TEST_COSTI):
            st.info("Lo scenario richiede tutte e sette le voci di costo di prova complete.")
            return
        if not _nessun_altro_costo(client, anno["id"]):
            st.info("Sono presenti ulteriori spese: lo scenario dimostrativo è sospeso.")
            return
        impostazioni = (client.table("vehicle_year_settings")
                        .select("vehicle_id,annual_km_limit,excess_km_penalty")
                        .eq("fiscal_year_id", anno["id"]).execute()).data or []
        km = (client.table("vehicle_monthly")
              .select("vehicle_id,month,distance_km")
              .eq("fiscal_year_id", anno["id"]).execute()).data or []
        penale = _penale(impostazioni, km)
        if penale is not None and penale != 0:
            st.info("Penale chilometrica stimata diversa da zero: completare i costi prima dello scenario.")
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
        st.error("Impossibile leggere lo scenario INPS. Nessun dato modificato.")
        return
    st.warning("SCENARIO DI PROVA: aliquote e importi non verificati per il 2027. "
               "Non sono contributi da versare e non modificano il fatturato.")
    st.dataframe([
        {"Passaggio": "Fatturato annuo stimato (invariato)", "Importo": euro(fatturato.quantize(CENT, rounding=ROUND_HALF_UP))},
        {"Passaggio": "Costi deducibili stimati", "Importo": euro(deducibili.quantize(CENT, rounding=ROUND_HALF_UP))},
        {"Passaggio": "Enasarco stimato (separato)", "Importo": euro(enasarco.quantize(CENT, rounding=ROUND_HALF_UP))},
        {"Passaggio": "1 · Imponibile INPS · scenario", "Importo": euro(imponibile.quantize(CENT, rounding=ROUND_HALF_UP))},
        {"Passaggio": "2 · INPS eccedente · scenario", "Importo": euro(eccedente.quantize(CENT, rounding=ROUND_HALF_UP))},
        {"Passaggio": "INPS fisso · scenario", "Importo": euro(p["inps_fisso_foglio"].quantize(CENT, rounding=ROUND_HALF_UP))},
        {"Passaggio": "3 · INPS complessivo · scenario", "Importo": euro(totale.quantize(CENT, rounding=ROUND_HALF_UP))},
    ], hide_index=True, width="stretch")
    st.caption("L'Enasarco non riduce il fatturato registrato: entra separatamente "
               "nella specifica formula dell'imponibile dello scenario.")
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
            st.success("Verifica numerica del caso dimostrativo riuscita.")
        else:
            st.warning("Il caso dimostrativo presenta differenze: controlla i dati a monte.")
    st.caption("Il massimale INPS 122.295 € è un parametro di prova non confermato per il 2027. "
               "I contributi pagati hanno un registro separato.")
