"""Scenario matematico del conto economico: sola lettura, dati di prova separati.

Non utilizza le stime come versamenti reali e non determina importi fiscali
definitivi, liquidazioni IVA o disponibilita' finanziaria.
"""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from costi_tabella import _penale
from detrazioni_deduzioni import PROVE, _annuale
from fatturato import NOTA_TEST, euro, importo_valido, leggi_fatturato, riepilogo
from imposte_enasarco import calcola_confronto
from imposte_inps import _nessun_altro_costo, calcola_inps_foglio
from imposte_irpef import calcola_irpef_foglio
from imposte_parametri import _leggi as leggi_parametri
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI, calcola_riepilogo
from riepilogo_laterale import tabella_laterale

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


def _valuta(importo: D) -> str:
    return euro(importo.quantize(CENT, rounding=ROUND_HALF_UP))


def detrazioni_anteprima_foglio() -> D:
    """Detrazione matematica del dataset di test, non registrazione reale."""
    return sum((_annuale(D(importo), rate, D(tasso), sanitaria)
                for _nome, importo, rate, _numero, tasso, sanitaria in PROVE), D("0"))


def calcola_conto_foglio(fatturato: D, iva_costi: D, costi_netti: D,
                          costi_deducibili: D, enasarco: D, ap: D,
                          fondo: D, detrazioni: D, p: dict[str, D]) -> dict[str, D]:
    """Trascrizione invariata delle formule del modello di riferimento."""
    imponibile_inps, inps_eccedente, inps = calcola_inps_foglio(
        fatturato, costi_deducibili, enasarco,
        p["inps_fisso_foglio"], p["inps_minimale_foglio"],
        p["inps_aliquota_prima_foglio"], p["inps_soglia_seconda_foglio"],
        p["inps_aliquota_seconda_foglio"], p["inps_massimale_foglio"],
    )
    imponibile_irpef, irpef, veneto, verona, imposte = calcola_irpef_foglio(
        fatturato, costi_deducibili, enasarco, ap, p["inps_fisso_foglio"], fondo,
        p["irpef_aliquota_1_foglio"], p["irpef_soglia_2_foglio"],
        p["irpef_aliquota_2_foglio"], p["irpef_soglia_3_foglio"],
        p["irpef_aliquota_3_foglio"], p["addizionale_veneto_foglio"],
        p["addizionale_verona_foglio"],
    )
    # B16 e' gia' nella base IRPEF: non sottrarre due volte il fondo pensione.
    netto = fatturato - inps - costi_netti - imposte - enasarco + detrazioni
    netto_senza_costi = fatturato - inps - imposte - enasarco + detrazioni
    return {
        "B1": fatturato,
        "B5": fatturato * D("0.22"),
        "B6": fatturato * D("0.22") - iva_costi,
        "B8": imponibile_inps,
        "B9": imponibile_irpef,
        "B11": inps,
        "B12": enasarco,
        "B13": costi_netti,
        "B14": imposte,
        "B15": detrazioni,
        "B16": fondo,
        "B18": netto,
        "B19": netto / D("12"),
        "B21": netto_senza_costi,
        "B22": netto_senza_costi / D("12"),
        "INPS_ECCEDENTE": inps_eccedente,
        "IRPEF": irpef,
        "VENETO": veneto,
        "VERONA": verona,
    }


# Ordine e significato delle voci del prospetto originario, senza codici cella
# o spiegazioni tecniche nella presentazione all'utente.
VOCI_CONTO = (
    ("B1", "Fatturato stimato integrale"),
    ("B5", "IVA fatturata · ipotesi 22%"),
    ("B6", "Differenza IVA · ipotesi, non debito"),
    ("B8", "Imponibile INPS · scenario"),
    ("B9", "Imponibile IRPEF · scenario"),
    ("B11", "Contributi INPS stimati"),
    ("B12", "Enasarco stimato · separato"),
    ("B13", "Costi netti stimati"),
    ("B14", "IRPEF e addizionali stimate"),
    ("B15", "Detrazioni · scenario"),
    ("B16", "Deduzioni · pensione, scenario"),
    ("B18", "Netto annuo teorico"),
    ("B19", "Netto teorico / 12"),
    ("B21", "Netto teorico senza costi"),
    ("B22", "Netto teorico senza costi / 12"),
)


def mostra_conto_economico(client: Client, anno: dict, sidebar_slot=None) -> None:
    """Lascia qui i controlli; rende il prospetto a due colonne nella sidebar."""
    st.subheader("Scenario di conto economico")
    st.warning("SOLO SIMULAZIONE: i parametri fiscali e la spettanza delle detrazioni "
               "non sono verificati. Il netto qui mostrato NON è liquidità disponibile.")
    st.caption("Lo scenario di prova utilizza solo dati dimostrativi. I contributi di anni "
               "precedenti, il fondo pensione e le detrazioni ipotetiche non vengono "
               "salvati né confusi con le registrazioni reali.")
    try:
        presenti = leggi_parametri(client, anno["id"])
        if any(k not in presenti for k in RICHIESTI):
            st.info("Completa prima i parametri nella scheda Imposte.")
            return
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        if not mandanti or not ricavi or any(r.get("notes") != NOTA_TEST for r in ricavi):
            st.info("Scenario dimostrativo sospeso: sono necessari esclusivamente "
                    "ricavi di prova. Le registrazioni effettive sono riportate sopra.")
            return
        dati_mandanti, _totale_registrato, fatturato = riepilogo(mandanti, ricavi)
        if fatturato is None or any(r["mesi"] == 0 for r in dati_mandanti):
            st.info("Per lo scenario serve almeno un mese registrato per ciascuna mandante.")
            return
        p = {k: D(str(presenti[k]["value"])) for k in RICHIESTI}
        _dettagli, enasarco, mono = calcola_confronto(
            mandanti, ricavi, p["enasarco_tasso_foglio"],
            p["enasarco_massimale_pluri"],
        )
        if mono:
            st.info("È presente una mandante monomandataria: questo scenario Enasarco "
                    "non può essere applicato automaticamente.")
            return
        costi, mancanti_costi, non_test = calcola_riepilogo(client, anno["id"])
        if non_test or mancanti_costi or len(costi) != len(VOCI) or not _nessun_altro_costo(client, anno["id"]):
            st.info("Scenario dimostrativo sospeso: servono le sette voci di costo di prova "
                    "complete, senza ulteriori spese o parametri modificati.")
            return
        impostazioni = (client.table("vehicle_year_settings")
                        .select("vehicle_id,annual_km_limit,excess_km_penalty")
                        .eq("fiscal_year_id", anno["id"]).execute()).data or []
        km = (client.table("vehicle_monthly")
              .select("vehicle_id,month,distance_km")
              .eq("fiscal_year_id", anno["id"]).execute()).data or []
        if _penale(impostazioni, km) != D("0"):
            st.info("Scenario sospeso: controlla la penale chilometrica nella scheda Auto.")
            return
        iva_costi = sum((r["IVA"] for r in costi), D("0"))
        costi_netti = sum((r["Netto"] for r in costi), D("0"))
        deducibili = sum((r["Deducibile"] for r in costi), D("0"))
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere i dati dello scenario. Nessun dato modificato.")
        return

    st.markdown("### Parametri dello scenario · nessun salvataggio")
    if st.button("Usa importi dimostrativi", key="ce_carica_prova"):
        st.session_state["ce_contributi_ap"] = "8000,00"
        st.session_state["ce_fondo_pensione"] = "5300,00"
        st.session_state["ce_scenario_foglio"] = True
    ap_testo = st.text_input("Contributi anni precedenti · scenario (€)",
                             key="ce_contributi_ap", placeholder="es. 8000,00")
    fondo_testo = st.text_input("Fondo pensione · scenario (€)",
                                key="ce_fondo_pensione", placeholder="es. 5300,00")
    st.caption("La detrazione dimostrativa è un valore matematico: non deriva da "
               "ricevute o pagamenti salvati nel gestionale.")
    if not st.session_state.get("ce_scenario_foglio") or not ap_testo.strip() or not fondo_testo.strip():
        st.info("Usa gli importi dimostrativi per completare lo scenario. "
                "Il riepilogo laterale continua a mostrare i dati registrati.")
        return
    try:
        ap = importo_valido(ap_testo)
        fondo = importo_valido(fondo_testo)
        valori = calcola_conto_foglio(fatturato, iva_costi, costi_netti, deducibili,
                                      enasarco, ap, fondo, detrazioni_anteprima_foglio(), p)
    except ValueError as exc:
        st.warning(str(exc))
        return
    righe = [{"VOCE": nome, "VALORE": _valuta(valori[cella])}
             for cella, nome in VOCI_CONTO]
    if sidebar_slot is None:
        tabella_laterale(righe, scenario=True)
    else:
        with sidebar_slot.container():
            tabella_laterale(righe, scenario=True)
    st.info("Lo scenario è visibile nel Conto economico della barra laterale.")
    st.caption("Il fondo pensione e i contributi di anni precedenti sono già considerati "
               "nella base IRPEF; non vanno sottratti una seconda volta. "
               "L'IVA indicata non è una liquidazione per periodo.")
