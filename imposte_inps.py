"""Scenario INPS coerente con il modello definitivo 2027.

Il fatturato resta integrale. L'Enasarco è una voce separata e NON riduce
l'imponibile INPS. Prima dell'imponibile viene applicata la deduzione
forfettaria agenti configurata nei parametri annuali.
"""
from decimal import Decimal as D, ROUND_HALF_UP
import streamlit as st
from supabase import Client

from calcoli_fiscali import calcola_inps_previsionale, parametri_agenti
from fatturato import NOTA_TEST, euro, leggi_fatturato, riepilogo
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI as VOCI_TEST_COSTI, calcola_riepilogo

CENT=D("0.01")
PARAMETRI=(
    "inps_fisso_foglio","inps_minimale_foglio","inps_aliquota_prima_foglio",
    "inps_soglia_seconda_foglio","inps_aliquota_seconda_foglio","inps_massimale_foglio",
    "agenti_soglia_1_foglio","agenti_aliquota_1_foglio",
    "agenti_soglia_2_foglio","agenti_aliquota_2_foglio",
    "agenti_soglia_3_foglio","agenti_aliquota_3_foglio",
)

def calcola_inps_foglio(fatturato:D,costi_deducibili:D,fisso:D,minimale:D,
                        prima:D,soglia:D,seconda:D,massimale:D,
                        agenti:tuple[D,D,D,D,D,D]) -> tuple[D,D,D,D]:
    r=calcola_inps_previsionale(
        fatturato,costi_deducibili,fisso=fisso,minimale=minimale,
        aliquota_prima=prima,soglia_seconda=soglia,
        aliquota_seconda=seconda,massimale=massimale,agenti=agenti)
    return r["imponibile_inps"],r["inps_eccedente"],r["inps_totale"],r["deduzione_agenti"]

def _nessun_altro_costo(client:Client,anno_id:str)->bool:
    categorie=(client.table("cost_categories").select("id,code").eq("fiscal_year_id",anno_id).execute()).data or []
    esterne={c["id"] for c in categorie if c["code"] not in VOCI_TEST_COSTI}
    if not esterne: return True
    stime=(client.table("annual_cost_estimates").select("category_id,estimated_gross_amount").eq("fiscal_year_id",anno_id).execute()).data or []
    spese=(client.table("costs").select("category_id,gross_amount").eq("fiscal_year_id",anno_id).execute()).data or []
    return not any(r["category_id"] in esterne and D(str(r[campo]))!=0
                   for gruppo,campo in ((stime,"estimated_gross_amount"),(spese,"gross_amount")) for r in gruppo)

def mostra_confronto_inps(client:Client,anno:dict,presenti:dict)->None:
    st.divider(); st.subheader("INPS · previsione")
    if any(k not in presenti for k in PARAMETRI):
        st.info("Completa i parametri INPS e la deduzione agenti per visualizzare la previsione."); return
    try:
        mandanti=elenco_mandanti(client); ricavi=leggi_fatturato(client,anno["id"])
        if not mandanti or not ricavi: st.info("Inserisci prima il fatturato."); return
        dati,_,fatturato=riepilogo(mandanti,ricavi)
        if fatturato is None or any(x["mesi"]==0 for x in dati):
            st.info("Serve almeno un mese compilato per ciascuna mandante."); return
        costi,mancanti,non_test=calcola_riepilogo(client,anno["id"])
        if non_test or mancanti or len(costi)!=len(VOCI_TEST_COSTI) or not _nessun_altro_costo(client,anno["id"]):
            st.info("Il confronto dimostrativo richiede le voci del foglio complete e senza costi aggiuntivi."); return
        deducibili=sum((r["Deducibile"] for r in costi),D("0"))
        p={k:D(str(presenti[k]["value"])) for k in PARAMETRI}
        imponibile,eccedente,totale,ded_ag=calcola_inps_foglio(
            fatturato,deducibili,p["inps_fisso_foglio"],p["inps_minimale_foglio"],
            p["inps_aliquota_prima_foglio"],p["inps_soglia_seconda_foglio"],
            p["inps_aliquota_seconda_foglio"],p["inps_massimale_foglio"],parametri_agenti(p))
    except ValueError as exc:
        st.warning(str(exc)); return
    except Exception:
        st.error("Impossibile calcolare la previsione INPS."); return
    if any(r.get("notes")==NOTA_TEST for r in ricavi):
        st.warning("DATI DI PROVA: il prospetto serve solo al confronto con il modello.")
    st.dataframe([
        {"Passaggio":"Fatturato annuo stimato","Importo":euro(fatturato.quantize(CENT,rounding=ROUND_HALF_UP))},
        {"Passaggio":"Costi fiscalmente deducibili","Importo":euro(deducibili.quantize(CENT,rounding=ROUND_HALF_UP))},
        {"Passaggio":"Deduzione forfettaria agenti","Importo":euro(ded_ag.quantize(CENT,rounding=ROUND_HALF_UP))},
        {"Passaggio":"Imponibile INPS","Importo":euro(imponibile.quantize(CENT,rounding=ROUND_HALF_UP))},
        {"Passaggio":"INPS eccedente stimato","Importo":euro(eccedente.quantize(CENT,rounding=ROUND_HALF_UP))},
        {"Passaggio":"INPS fisso","Importo":euro(p["inps_fisso_foglio"].quantize(CENT,rounding=ROUND_HALF_UP))},
        {"Passaggio":"INPS complessivo stimato","Importo":euro(totale.quantize(CENT,rounding=ROUND_HALF_UP))},
    ],hide_index=True,width="stretch")
    st.caption("L'Enasarco non viene sottratto dall'imponibile INPS. I parametri restano provvisori finché non saranno pubblicati quelli ufficiali 2027.")
