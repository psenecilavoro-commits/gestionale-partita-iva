"""Accantonamenti: scenario matematico di prova senza scritture a Supabase.

Fatturato e provvigioni nette restano distinti. Il risultato non rappresenta
liquidita', imposte o contributi realmente dovuti.
"""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from costi_tabella import _penale
from fatturato import NOTA_TEST, euro, importo_valido, leggi_fatturato, riepilogo
from imposte_enasarco import calcola_confronto
from imposte_inps import _nessun_altro_costo, calcola_inps_foglio
from imposte_irpef import calcola_irpef_foglio
from imposte_parametri import _leggi as leggi_parametri
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI, calcola_riepilogo

D = Decimal
CENT = D("0.01")
RICHIESTI = (
    "enasarco_tasso_foglio", "enasarco_massimale_pluri",
    "inps_fisso_foglio", "inps_minimale_foglio", "inps_aliquota_prima_foglio",
    "inps_soglia_seconda_foglio", "inps_aliquota_seconda_foglio", "inps_massimale_foglio",
    "irpef_aliquota_1_foglio", "irpef_soglia_2_foglio", "irpef_aliquota_2_foglio",
    "irpef_soglia_3_foglio", "irpef_aliquota_3_foglio",
    "addizionale_veneto_foglio", "addizionale_verona_foglio",
)


def obiettivo_annuo_foglio(fatturato: D, inps: D, irpef: D,
                           veneto: D, verona: D, avanzo_ap: D = D("0")) -> D:
    """Formula matematica originaria; coefficiente 11,5% NON validato fiscalmente."""
    valori = (fatturato, inps, irpef, veneto, verona, avanzo_ap)
    if any(not n.is_finite() or n < 0 for n in valori):
        raise ValueError("Importi del confronto non validi")
    return inps + irpef + veneto + verona - fatturato * D("0.115") - avanzo_ap


def quota_mesi_vuoti_foglio(obiettivo: D, gia_accantonato: D,
                            mesi_compilati: int) -> D | None:
    """Distribuzione residua su 12 meno i mesi gia' compilati."""
    if (not obiettivo.is_finite() or not gia_accantonato.is_finite()
            or gia_accantonato < 0 or type(mesi_compilati) is not int
            or not 0 <= mesi_compilati <= 12):
        raise ValueError("Scenario accantonamenti non valido")
    if mesi_compilati == 0 and gia_accantonato != 0:
        raise ValueError("Non puoi indicare accantonamenti senza mesi compilati")
    if mesi_compilati == 12:
        return None
    return (obiettivo - gia_accantonato) / D(12 - mesi_compilati)


def _euro(n: D) -> str:
    return euro(n.quantize(CENT, rounding=ROUND_HALF_UP))


def mostra_confronto_accantonamenti(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Quota mensile residua · scenario")
    st.warning("SOLO SCENARIO DI PROVA: il coefficiente 11,5%, i parametri e gli importi "
               "non sono verificati come somme da versare. Non crea accantonamenti o movimenti.")
    st.caption("Le provvigioni nette sono importi inseriti manualmente e distinti dal "
               "fatturato; non sono un netto fiscale.")
    try:
        presenti = leggi_parametri(client, anno["id"])
        if any(k not in presenti for k in RICHIESTI):
            st.info("Per lo scenario completa prima i parametri nella scheda Imposte.")
            return
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        if not mandanti or not ricavi or any(r.get("notes") != NOTA_TEST for r in ricavi):
            st.info("Scenario dimostrativo non disponibile: richiede esclusivamente ricavi di prova.")
            return
        righe, _registrato, fatturato = riepilogo(mandanti, ricavi)
        if fatturato is None or any(r["mesi"] == 0 for r in righe):
            st.info("Occorre almeno un mese compilato per ciascuna mandante di prova.")
            return
        p = {k: D(str(presenti[k]["value"])) for k in RICHIESTI}
        _dettagli, enasarco, mono = calcola_confronto(
            mandanti, ricavi, p["enasarco_tasso_foglio"], p["enasarco_massimale_pluri"]
        )
        if mono:
            st.info("Mandante monomandataria presente: scenario Enasarco non applicabile automaticamente.")
            return
        costi, mancanti, non_test = calcola_riepilogo(client, anno["id"])
        if non_test or mancanti or len(costi) != len(VOCI) or not _nessun_altro_costo(client, anno["id"]):
            st.info("Lo scenario richiede le sette voci di costo di prova complete, senza altre spese.")
            return
        impostazioni = (client.table("vehicle_year_settings")
                        .select("vehicle_id,annual_km_limit,excess_km_penalty")
                        .eq("fiscal_year_id", anno["id"]).execute()).data or []
        km = (client.table("vehicle_monthly")
              .select("vehicle_id,month,distance_km")
              .eq("fiscal_year_id", anno["id"]).execute()).data or []
        penale = _penale(impostazioni, km)
        if penale is None or penale != D("0"):
            st.info("Controlla prima la penale chilometrica nella scheda Auto: deve essere zero per questo scenario.")
            return
        deducibili = sum((r["Deducibile"] for r in costi), D("0"))
        _imponibile, _eccedente, inps = calcola_inps_foglio(
            fatturato, deducibili, enasarco,
            p["inps_fisso_foglio"], p["inps_minimale_foglio"],
            p["inps_aliquota_prima_foglio"], p["inps_soglia_seconda_foglio"],
            p["inps_aliquota_seconda_foglio"], p["inps_massimale_foglio"],
        )
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Lettura dello scenario non riuscita; nessun dato modificato.")
        return
    if st.button("Usa importi dimostrativi · accantonamenti", key="acc_scenario_prova"):
        st.session_state["acc_contributi_ap_prova"] = "8000,00"
        st.session_state["acc_fondo_prova"] = "5300,00"
    col1, col2 = st.columns(2)
    with col1:
        ap_testo = st.text_input("Contributi anni precedenti · scenario (€)",
                                 key="acc_contributi_ap_prova", placeholder="es. 8000,00")
    with col2:
        fondo_testo = st.text_input("Fondo pensione · scenario (€)",
                                    key="acc_fondo_prova", placeholder="es. 5300,00")
    if not ap_testo.strip() or not fondo_testo.strip():
        st.info("Usa gli importi dimostrativi o compila entrambi i valori di prova.")
        return
    try:
        ap = importo_valido(ap_testo)
        fondo = importo_valido(fondo_testo)
        _base, irpef, veneto, verona, _totale = calcola_irpef_foglio(
            fatturato, deducibili, enasarco, ap, p["inps_fisso_foglio"], fondo,
            p["irpef_aliquota_1_foglio"], p["irpef_soglia_2_foglio"],
            p["irpef_aliquota_2_foglio"], p["irpef_soglia_3_foglio"],
            p["irpef_aliquota_3_foglio"], p["addizionale_veneto_foglio"],
            p["addizionale_verona_foglio"],
        )
        obiettivo = obiettivo_annuo_foglio(fatturato, inps, irpef, veneto, verona)
    except ValueError as exc:
        st.warning(str(exc))
        return
    testo_avanzo = st.text_input("Avanzo anni precedenti · solo scenario (€)", value="0,00", key="acc_avanzo_ap")
    try:
        obiettivo -= importo_valido(testo_avanzo)
    except ValueError as exc:
        st.warning(str(exc))
        return
    st.metric("Obiettivo annuo · ipotesi, NON importo dovuto", _euro(obiettivo))
    st.caption("Calcolo: INPS fisso + INPS eccedente + IRPEF + addizionali Veneto/Verona "
               "− 11,5% del fatturato stimato − avanzo anni precedenti. "
               "Il coefficiente è solo un'ipotesi da verificare; il fatturato registrato non cambia.")
    st.markdown("#### Ripartizione sui mesi ancora vuoti")
    st.caption("I campi servono soltanto a simulare le riserve mensili: non leggono "
               "né sovrascrivono gli accantonamenti registrati.")
    a, b = st.columns(2)
    with a:
        mesi = st.number_input("Mesi già compilati nello scenario", min_value=0, max_value=12,
                               step=1, value=0, key="acc_mesi_scenario")
    with b:
        testo_riserve = st.text_input("Totale già accantonato nello scenario (€)",
                                      value="0,00", key="acc_totale_scenario")
    try:
        gia = importo_valido(testo_riserve)
        quota = quota_mesi_vuoti_foglio(obiettivo, gia, int(mesi))
    except ValueError as exc:
        st.warning(str(exc))
        return
    if quota is None:
        st.info("Tutti i 12 mesi sono compilati: nessuna quota residua da ripartire.")
    else:
        st.metric("Quota per ogni mese ancora vuoto · scenario", _euro(quota))
        st.caption(f"({_euro(obiettivo)} − {_euro(gia)}) / {12 - int(mesi)} mesi da compilare. "
                   "Uno zero registrato conta come mese compilato.")
    if obiettivo < gia:
        st.warning("Le riserve ipotizzate superano l'obiettivo: la quota residua "
                   "può essere negativa. Non è un ordine di disinvestimento o rimborso.")
    st.caption("Le provvigioni nette manuali, il quadro mensile e i prospetti IVA documentali "
               "sono nelle rispettive sezioni; questo scenario non li sovrascrive.")
