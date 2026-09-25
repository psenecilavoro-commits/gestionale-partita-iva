"""Conto economico previsionale allineato al foglio definitivo 2027."""
from decimal import Decimal as D, ROUND_HALF_UP
import streamlit as st
from supabase import Client

from calcoli_fiscali import conto_previsionale
from detrazioni_deduzioni import PROVE, _annuale
from fatturato import euro, leggi_fatturato, riepilogo
from imposte_enasarco import calcola_confronto
from imposte_parametri import _leggi as leggi_parametri
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI, calcola_riepilogo

CENT=D("0.01")
RICHIESTI=(
 "enasarco_tasso_foglio","enasarco_massimale_pluri",
 "inps_fisso_foglio","inps_minimale_foglio","inps_aliquota_prima_foglio",
 "inps_soglia_seconda_foglio","inps_aliquota_seconda_foglio","inps_massimale_foglio",
 "agenti_soglia_1_foglio","agenti_aliquota_1_foglio","agenti_soglia_2_foglio",
 "agenti_aliquota_2_foglio","agenti_soglia_3_foglio","agenti_aliquota_3_foglio",
 "irpef_aliquota_1_foglio","irpef_soglia_2_foglio","irpef_aliquota_2_foglio",
 "irpef_soglia_3_foglio","irpef_aliquota_3_foglio",
 "addizionale_veneto_foglio","addizionale_verona_foglio",
)

def _valuta(x:D)->str: return euro(x.quantize(CENT,rounding=ROUND_HALF_UP))

def detrazioni_anteprima_foglio()->D:
    return sum((_annuale(D(importo),rate,D(tasso),sanitaria)
                for _nome,importo,rate,_numero,tasso,sanitaria in PROVE),D("0"))

def calcola_conto_foglio(fatturato:D,iva_costi:D,costi_netti:D,costi_deducibili:D,
                         enasarco:D,contributi_ap:D,fondo:D,detrazioni:D,p:dict[str,D])->dict[str,D]:
    """Riproduce il modello definitivo.

    Per il benchmark del foglio la quota INPS fissa è assunta pagata nell'anno
    insieme ai contributi A.P.; l'eccedenza maturata non viene dedotta dalla
    base IRPEF finché non è pagata.
    """
    r=conto_previsionale(
        fatturato=fatturato,costi_netti=costi_netti,costi_deducibili=costi_deducibili,
        enasarco_stimato=enasarco,
        contributi_irpef=contributi_ap+p["inps_fisso_foglio"],
        pensione_deducibile=fondo,detrazioni=detrazioni,p=p)
    return {
      "B1":fatturato,
      "B5":fatturato*D("0.22"),
      "B6":fatturato*D("0.22")-iva_costi,
      "DED_AGENTI":r["deduzione_agenti"],
      "B8":r["imponibile_inps"],
      "B9":r["imponibile_irpef"],
      "B11":r["inps_totale"],
      "B12":enasarco,
      "B13":costi_netti,
      "B14":r["imposte_lorde"],
      "B15":r["detrazioni_usate"],
      "B16":fondo,
      "B18":r["netto"],
      "B19":r["netto_mese"],
      "B21":r["netto_no_costi"],
      "B22":r["netto_no_costi_mese"],
      "INPS_ECCEDENTE":r["inps_eccedente"],
      "IRPEF":r["irpef_lorda"],
      "VENETO":r["addizionale_regionale"],
      "VERONA":r["addizionale_comunale"],
      "IMPOSTE_NETTE":r["imposte_nette"],
    }

VOCI_CONTO=(
 ("B1","Fatturato stimato integrale"),
 ("DED_AGENTI","Deduzione forfettaria agenti"),
 ("B8","Imponibile INPS"),
 ("B9","Imponibile IRPEF"),
 ("B11","Contributi INPS stimati"),
 ("B12","Enasarco stimato"),
 ("B13","Costi netti stimati"),
 ("B14","IRPEF + addizionali prima delle detrazioni"),
 ("B15","Detrazioni utilizzate"),
 ("B16","Fondo pensione deducibile"),
 ("B18","Netto annuo teorico"),
 ("B19","Netto teorico / 12"),
 ("B21","Netto teorico senza costi"),
 ("B22","Netto teorico senza costi / 12"),
)

def mostra_conto_economico(client:Client,anno:dict,sidebar_slot=None)->None:
    st.subheader("Conto economico · modello definitivo")
    st.caption("Il prospetto replica il modello 2027 approvato. I parametri fiscali annuali restano configurabili finché non saranno ufficiali.")
    try:
        presenti=leggi_parametri(client,anno["id"])
        if any(k not in presenti for k in RICHIESTI):
            st.info("Completa i parametri nella scheda Imposte."); return
        mandanti=elenco_mandanti(client); ricavi=leggi_fatturato(client,anno["id"])
        dati,_,fatturato=riepilogo(mandanti,ricavi)
        if fatturato is None or any(x["mesi"]==0 for x in dati):
            st.info("Completa almeno un mese per ogni mandante."); return
        p={k:D(str(presenti[k]["value"])) for k in RICHIESTI}
        _,enasarco,mono=calcola_confronto(mandanti,ricavi,p["enasarco_tasso_foglio"],p["enasarco_massimale_pluri"])
        if mono:
            st.info("Completa la gestione Enasarco monomandataria prima del prospetto."); return
        costi,mancanti,non_test=calcola_riepilogo(client,anno["id"])
        if mancanti or non_test or len(costi)!=len(VOCI):
            st.info("Il confronto automatico richiede le voci del modello complete."); return
        iva=sum((r["IVA"] for r in costi),D("0"))
        netto=sum((r["Netto"] for r in costi),D("0"))
        ded=sum((r["Deducibile"] for r in costi),D("0"))
    except Exception:
        st.error("Impossibile costruire il conto economico."); return
    ap=st.number_input("Contributi anni precedenti effettivamente pagati nell'anno (€)",min_value=0.0,value=8000.0,step=100.0)
    fondo=st.number_input("Fondo pensione deducibile (€)",min_value=0.0,value=5300.0,step=100.0)
    valori=calcola_conto_foglio(fatturato,iva,netto,ded,enasarco,D(str(ap)),D(str(fondo)),detrazioni_anteprima_foglio(),p)
    st.dataframe([{"Voce":nome,"Importo":_valuta(valori[codice])} for codice,nome in VOCI_CONTO],hide_index=True,width="stretch")
    st.caption("Deduzioni e fondo pensione incidono sulla base IRPEF e non vengono sottratti una seconda volta dal netto.")
