"""Conto economico: confronto matematico con il foglio originale, SOLA LETTURA.

Non usa i valori del foglio come versamenti reali, non modifica Supabase e
non determina imposte dovute, liquidazioni IVA o denaro disponibile.
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
    """F19: somma delle formule grigie, NON detrazioni presenti nel database."""
    return sum((_annuale(D(importo), rate, D(tasso), sanitaria)
                for _nome, importo, rate, _numero, tasso, sanitaria in PROVE), D("0"))


def calcola_conto_foglio(fatturato: D, iva_costi: D, costi_netti: D,
                          costi_deducibili: D, enasarco: D, ap: D,
                          fondo: D, detrazioni: D, p: dict[str, D]) -> dict[str, D]:
    """Trascrive Conto economico!B1:B22 senza arrotondamenti intermedi."""
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
    # B18 = B1-B11-B13-B14-B12+B15: B16 NON viene sottratto di nuovo.
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


def mostra_conto_economico(client: Client, anno: dict) -> None:
    st.subheader("Conto economico · confronto con il foglio")
    st.warning("SOLO SIMULAZIONE: i parametri fiscali 2027 e la spettanza delle detrazioni "
               "non sono verificati. Il netto qui mostrato NON è liquidità o reddito disponibile.")
    st.caption("Questa prima versione usa i ricavi e i sette costi DI PROVA già verificati. "
               "I contributi A.P., il fondo pensione e le detrazioni del foglio sono uno "
               "scenario temporaneo: non vengono salvati né confusi con le registrazioni reali.")
    try:
        presenti = leggi_parametri(client, anno["id"])
        mancanti_parametri = [k for k in RICHIESTI if k not in presenti]
        if mancanti_parametri:
            st.info("Completa prima i gruppi di parametri nella scheda Imposte.")
            return
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        if not mandanti or not ricavi or any(r.get("notes") != NOTA_TEST for r in ricavi):
            st.info("Confronto sospeso: occorrono solo i ricavi etichettati come dati di prova. "
                    "Le registrazioni effettive hanno uno scenario distinto nella sezione precedente.")
            return
        dati_mandanti, _totale_registrato, fatturato = riepilogo(mandanti, ricavi)
        if fatturato is None or any(r["mesi"] == 0 for r in dati_mandanti):
            st.info("Per il confronto serve almeno un mese registrato per ciascuna mandante.")
            return
        p = {k: D(str(presenti[k]["value"])) for k in RICHIESTI}
        _dettagli, enasarco, mono = calcola_confronto(
            mandanti, ricavi, p["enasarco_tasso_foglio"],
            p["enasarco_massimale_pluri"],
        )
        if mono:
            st.info("È presente una mandante monomandataria: la formula Enasarco "
                    "del foglio non può essere applicata automaticamente.")
            return
        costi, mancanti_costi, non_test = calcola_riepilogo(client, anno["id"])
        if non_test or mancanti_costi or len(costi) != len(VOCI) or not _nessun_altro_costo(client, anno["id"]):
            st.info("Confronto sospeso: servono le sette voci Costi di prova complete, "
                    "senza altre spese o parametri modificati.")
            return
        impostazioni = (client.table("vehicle_year_settings")
                        .select("vehicle_id,annual_km_limit,excess_km_penalty")
                        .eq("fiscal_year_id", anno["id"]).execute()).data or []
        km = (client.table("vehicle_monthly")
              .select("vehicle_id,month,distance_km")
              .eq("fiscal_year_id", anno["id"]).execute()).data or []
        penale = _penale(impostazioni, km)
        if penale != D("0"):
            st.info("Confronto sospeso: la penale km non è verificata come zero. "
                    "Completa o controlla le impostazioni nella scheda Auto.")
            return
        iva_costi = sum((r["IVA"] for r in costi), D("0"))
        costi_netti = sum((r["Netto"] for r in costi), D("0"))
        deducibili = sum((r["Deducibile"] for r in costi), D("0"))
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Non è stato possibile leggere i dati del confronto. Nessun dato modificato.")
        return

    st.markdown("### Scenario di confronto · nessun salvataggio")
    if st.button("Usa gli importi di prova del foglio", key="ce_carica_prova"):
        st.session_state["ce_contributi_ap"] = "8000,00"
        st.session_state["ce_fondo_pensione"] = "5300,00"
        st.session_state["ce_scenario_foglio"] = True
    ap_testo = st.text_input("Contributi anni precedenti · scenario (€)",
                             key="ce_contributi_ap", placeholder="es. 8000,00")
    fondo_testo = st.text_input("Fondo pensione · scenario (€)",
                                key="ce_fondo_pensione", placeholder="es. 5300,00")
    st.caption("La detrazione di confronto deriva dalle formule del foglio originale, "
               "non da detrazioni o ricevute salvate nel gestionale.")
    if not st.session_state.get("ce_scenario_foglio") or not ap_testo.strip() or not fondo_testo.strip():
        st.info("Premi «Usa gli importi di prova del foglio» per visualizzare il Conto economico di confronto.")
        return
    try:
        ap = importo_valido(ap_testo)
        fondo = importo_valido(fondo_testo)
        valori = calcola_conto_foglio(fatturato, iva_costi, costi_netti, deducibili,
                                      enasarco, ap, fondo, detrazioni_anteprima_foglio(), p)
    except ValueError as exc:
        st.warning(str(exc))
        return

    riferimenti = (
        ("B1", "Fatturato stimato integrale", "Fatturato!B41"),
        ("B5", "IVA fatturata · formula del foglio", "B1 × 22%"),
        ("B6", "IVA da versare · solo formula del foglio", "B5 − Costi!C14"),
        ("B8", "Imponibile INPS · formula del foglio", "B1 − Costi!F14 − Imposte!E4"),
        ("B9", "Imponibile IRPEF · formula del foglio", "B1 − F14 − E4 − B3 − B5 − I3"),
        ("B11", "Contributi INPS stimati", "Imposte!B5 + Imposte!B6"),
        ("B12", "Enasarco stimato · separato", "Imposte!E4"),
        ("B13", "Costi netti stimati", "Costi!D14"),
        ("B14", "IRPEF e addizionali stimate", "Imposte!B7 + B8 + B9"),
        ("B15", "Detrazioni · scenario del foglio", "Detrazioni e deduzioni!F19"),
        ("B16", "Deduzioni · fondo pensione scenario", "Detrazioni e deduzioni!I3:I19"),
        ("B18", "Netto annuo teorico del foglio", "B1 − B11 − B13 − B14 − B12 + B15"),
        ("B19", "Netto teorico / 12", "B18 / 12"),
        ("B21", "Netto teorico senza costi", "B1 − B11 − B14 − B12 + B15"),
        ("B22", "Netto teorico senza costi / 12", "B21 / 12"),
    )
    st.dataframe([{"Voce": nome, "Valore": _valuta(valori[cella]),
                   "Cella": f"Conto economico!{cella}", "Formula / origine": origine}
                  for cella, nome, origine in riferimenti], hide_index=True,
                 width="stretch")
    c1, c2 = st.columns(2)
    c1.metric("Netto annuo TEORICO · confronto", _valuta(valori["B18"]))
    c2.metric("Media teorica su 12 mesi", _valuta(valori["B19"]))
    st.caption("Il fondo pensione e i contributi A.P. sono già considerati nella base "
               "IRPEF: la formula del netto NON li sottrae un'altra volta. "
               "L'IVA mostrata non è una liquidazione per periodo.")

    attesi = {"B1": "115200.00", "B6": "22722.03", "B8": "99945.20",
              "B9": "82033.56", "B11": "24911.24", "B12": "5206.85",
              "B13": "13319.86", "B14": "29139.71", "B15": "2941.51",
              "B18": "45563.85", "B19": "3796.99", "B21": "58883.72",
              "B22": "4906.98"}
    parametri_foglio = {
        "enasarco_tasso_foglio": "0.085", "enasarco_massimale_pluri": "30057",
        "inps_fisso_foglio": "4611.64", "inps_minimale_foglio": "18808.01",
        "inps_aliquota_prima_foglio": "0.2448", "inps_soglia_seconda_foglio": "56224",
        "inps_aliquota_seconda_foglio": "0.2548", "inps_massimale_foglio": "122295",
        "irpef_aliquota_1_foglio": "0.23", "irpef_soglia_2_foglio": "28000",
        "irpef_aliquota_2_foglio": "0.33", "irpef_soglia_3_foglio": "50000",
        "irpef_aliquota_3_foglio": "0.43", "addizionale_veneto_foglio": "0.0123",
        "addizionale_verona_foglio": "0.008",
    }
    if ap == D("8000") and fondo == D("5300") and all(
        p[k] == D(v) for k, v in parametri_foglio.items()
    ):
        diversi = [cella for cella, atteso in attesi.items()
                   if valori[cella].quantize(CENT, rounding=ROUND_HALF_UP) != D(atteso)]
        if diversi:
            st.warning("Il confronto non coincide con il foglio nelle celle: " + ", ".join(diversi) + ".")
        else:
            st.success("Confronto matematico riuscito: 13 valori, inclusi netto annuo e media "
                       "mensile teorica, coincidono con il foglio di prova.")
    else:
        st.info("Scenario o parametri diversi dai valori del foglio: confronto numerico "
                "con gli importi originali non applicabile.")
