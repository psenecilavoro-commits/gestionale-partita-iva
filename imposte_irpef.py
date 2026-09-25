"""Previsione IRPEF/addizionali allineata al modello definitivo 2027."""
from decimal import Decimal as D, ROUND_HALF_UP
import streamlit as st
from supabase import Client

from calcoli_fiscali import calcola_inps_previsionale, calcola_irpef_da_base, parametri_agenti, parametri_irpef
from fatturato import euro, importo_valido, leggi_fatturato, riepilogo
from imposte_enasarco import calcola_confronto
from imposte_inps import _nessun_altro_costo
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI as VOCI_COSTI_TEST, calcola_riepilogo

CENT=D("0.01")
PARAMETRI=(
 "enasarco_tasso_foglio","enasarco_massimale_pluri",
 "inps_fisso_foglio","inps_minimale_foglio","inps_aliquota_prima_foglio",
 "inps_soglia_seconda_foglio","inps_aliquota_seconda_foglio","inps_massimale_foglio",
 "agenti_soglia_1_foglio","agenti_aliquota_1_foglio","agenti_soglia_2_foglio",
 "agenti_aliquota_2_foglio","agenti_soglia_3_foglio","agenti_aliquota_3_foglio",
 "irpef_aliquota_1_foglio","irpef_soglia_2_foglio","irpef_aliquota_2_foglio",
 "irpef_soglia_3_foglio","irpef_aliquota_3_foglio",
 "addizionale_veneto_foglio","addizionale_verona_foglio",
)

def calcola_irpef_foglio(base:D, prima:D,soglia_due:D,seconda:D,soglia_tre:D,
                         terza:D,aliquota_veneto:D,aliquota_verona:D):
    r=calcola_irpef_da_base(base,aliquota1=prima,soglia2=soglia_due,aliquota2=seconda,
                            soglia3=soglia_tre,aliquota3=terza,
                            addizionale_regionale=aliquota_veneto,
                            addizionale_comunale=aliquota_verona)
    return (r["imponibile_irpef"],r["irpef_lorda"],r["addizionale_regionale"],
            r["addizionale_comunale"],r["imposte_lorde"])

def _fmt(x): return euro(x.quantize(CENT,rounding=ROUND_HALF_UP))

def mostra_confronto_irpef(client:Client,anno:dict,presenti:dict)->None:
    st.divider(); st.subheader("IRPEF e addizionali · previsione")
    if any(k not in presenti for k in PARAMETRI):
        st.info("Completa prima parametri INPS, Enasarco, deduzione agenti e IRPEF."); return
    st.caption("La base IRPEF usa i contributi effettivamente pagati nell'anno. Qui puoi usare importi di scenario per confrontare il foglio definitivo.")
    ap_txt=st.text_input("Contributi INPS di anni precedenti pagati nell'anno · scenario (€)",key="irpef_ap",placeholder="es. 8000,00")
    fondo_txt=st.text_input("Fondo pensione deducibile · scenario (€)",key="irpef_fondo",placeholder="es. 5300,00")
    if not ap_txt.strip() or not fondo_txt.strip(): return
    try:
        ap=importo_valido(ap_txt); fondo=importo_valido(fondo_txt)
        mandanti=elenco_mandanti(client); ricavi=leggi_fatturato(client,anno["id"])
        dati,_,fatturato=riepilogo(mandanti,ricavi)
        if fatturato is None or any(x["mesi"]==0 for x in dati): st.info("Completa il fatturato."); return
        p={k:D(str(presenti[k]["value"])) for k in PARAMETRI}
        _,enasarco,mono=calcola_confronto(mandanti,ricavi,p["enasarco_tasso_foglio"],p["enasarco_massimale_pluri"])
        if mono: st.info("Mandante monomandataria presente: completa i parametri specifici prima del confronto."); return
        costi,mancanti,non_test=calcola_riepilogo(client,anno["id"])
        if non_test or mancanti or len(costi)!=len(VOCI_COSTI_TEST) or not _nessun_altro_costo(client,anno["id"]):
            st.info("Il confronto richiede le voci del modello complete."); return
        ded=sum((r["Deducibile"] for r in costi),D("0"))
        inps=calcola_inps_previsionale(fatturato,ded,fisso=p["inps_fisso_foglio"],
             minimale=p["inps_minimale_foglio"],aliquota_prima=p["inps_aliquota_prima_foglio"],
             soglia_seconda=p["inps_soglia_seconda_foglio"],aliquota_seconda=p["inps_aliquota_seconda_foglio"],
             massimale=p["inps_massimale_foglio"],agenti=parametri_agenti(p))
        # Il modello definitivo considera deducibili qui solo gli importi pagati:
        # scenario = AP + quota fissa INPS assunta pagata nell'anno.
        base=inps["imponibile_inps"]-enasarco-ap-p["inps_fisso_foglio"]-fondo
        tax=calcola_irpef_da_base(base,**parametri_irpef(p))
    except ValueError as exc:
        st.warning(str(exc)); return
    except Exception:
        st.error("Impossibile costruire la previsione IRPEF."); return
    st.dataframe([
      {"Passaggio":"Imponibile INPS di partenza","Importo":_fmt(inps["imponibile_inps"])},
      {"Passaggio":"Enasarco stimato","Importo":_fmt(enasarco)},
      {"Passaggio":"INPS anni precedenti pagato","Importo":_fmt(ap)},
      {"Passaggio":"INPS fisso assunto pagato","Importo":_fmt(p["inps_fisso_foglio"])},
      {"Passaggio":"Fondo pensione deducibile","Importo":_fmt(fondo)},
      {"Passaggio":"Imponibile IRPEF","Importo":_fmt(tax["imponibile_irpef"])},
      {"Passaggio":"IRPEF lorda","Importo":_fmt(tax["irpef_lorda"])},
      {"Passaggio":"Addizionale Veneto","Importo":_fmt(tax["addizionale_regionale"])},
      {"Passaggio":"Addizionale Verona","Importo":_fmt(tax["addizionale_comunale"])},
      {"Passaggio":"IRPEF + addizionali prima delle detrazioni","Importo":_fmt(tax["imposte_lorde"])},
    ],hide_index=True,width="stretch")
    st.caption("L'INPS eccedente maturato ma non ancora pagato non viene dedotto dalla base IRPEF. Le detrazioni riducono l'imposta successivamente.")
