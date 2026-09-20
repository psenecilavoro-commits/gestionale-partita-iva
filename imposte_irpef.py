"""Confronto IRPEF e addizionali del foglio: solo simulazione, nessun versamento.

Le cifre A.P. e fondo pensione del foglio si caricano SOLO su azione esplicita,
non diventano pagamenti, deduzioni fiscali validate o dati nel database.
Enasarco e' distinto dal fatturato e compare solo nelle formule del foglio.
"""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from costi_tabella import _penale
from fatturato import NOTA_TEST, euro, importo_valido, leggi_fatturato, riepilogo
from imposte_enasarco import calcola_confronto
from imposte_inps import _nessun_altro_costo
from mandanti import elenco_mandanti
from riepilogo_costi import VOCI as VOCI_COSTI_TEST, calcola_riepilogo

D = Decimal
CENT = D("0.01")
PARAMETRI = (
    "enasarco_tasso_foglio", "enasarco_massimale_pluri", "inps_fisso_foglio",
    "irpef_aliquota_1_foglio", "irpef_soglia_2_foglio", "irpef_aliquota_2_foglio",
    "irpef_soglia_3_foglio", "irpef_aliquota_3_foglio",
    "addizionale_veneto_foglio", "addizionale_verona_foglio",
)


def calcola_irpef_foglio(
    fatturato: D, deducibili: D, enasarco: D, contributi_ap: D,
    inps_fisso: D, fondo_pensione: D, prima: D, soglia_due: D,
    seconda: D, soglia_tre: D, terza: D, aliquota_veneto: D,
    aliquota_verona: D,
) -> tuple[D, D, D, D, D]:
    """Conto economico!B9; Imposte!B7:B9, senza arrotondamenti intermedi."""
    valori = (
        fatturato, deducibili, enasarco, contributi_ap, inps_fisso,
        fondo_pensione, prima, soglia_due, seconda, soglia_tre, terza,
        aliquota_veneto, aliquota_verona,
    )
    if any(not valore.is_finite() or valore < 0 for valore in valori):
        raise ValueError("Valori non validi: servono importi e aliquote non negativi e finiti.")
    if not D("0") < soglia_due < soglia_tre or any(
        aliquota > D("1") for aliquota in
        (prima, seconda, terza, aliquota_veneto, aliquota_verona)
    ):
        raise ValueError("Soglie o aliquote non coerenti: confrontiamole prima di continuare.")
    imponibile = (fatturato - deducibili - enasarco - contributi_ap
                  - inps_fisso - fondo_pensione)
    # Nel foglio la formula e' a scaglioni con soglie E11 ed E12.
    if imponibile < soglia_due:
        irpef = imponibile * prima
    elif imponibile < soglia_tre:
        irpef = soglia_due * prima + (imponibile - soglia_due) * seconda
    else:
        irpef = (soglia_due * prima + (soglia_tre - soglia_due) * seconda
                 + (imponibile - soglia_tre) * terza)
    veneto = imponibile * aliquota_veneto
    verona = imponibile * aliquota_verona
    return imponibile, irpef, veneto, verona, irpef + veneto + verona


def _valuta(valore: D) -> str:
    return euro(valore.quantize(CENT, rounding=ROUND_HALF_UP))


def mostra_confronto_irpef(client: Client, anno: dict, presenti: dict) -> None:
    st.divider()
    st.subheader("IRPEF e addizionali · confronto delle formule del foglio")
    st.caption("Tre blocchi: imponibile di confronto, IRPEF per scaglioni, addizionali Veneto e Verona. "
               "Non viene calcolata un'imposta effettivamente dovuta o un netto disponibile.")
    if any(codice not in presenti for codice in PARAMETRI):
        st.info("Per questo confronto occorrono tutti i parametri Enasarco, INPS fisso e IRPEF già caricati.")
        return

    st.warning(
        "ATTENZIONE: nel foglio i contributi A.P. sono 8.000 € e il fondo pensione 5.300 €. "
        "Sono importi DI PROVA, non pagamenti verificati. Non li salvo e non li considero "
        "deduzioni ammesse per il 2027."
    )
    if st.button("Usa 8.000 € A.P. e 5.300 € fondo pensione SOLO per il confronto", key="irpef_scenario_test"):
        st.session_state["irpef_ap_confronto"] = "8000,00"
        st.session_state["irpef_fondo_confronto"] = "5300,00"
    c1, c2 = st.columns(2)
    with c1:
        testo_ap = st.text_input(
            "Contributi anni precedenti versati nell'anno (€) · scenario",
            key="irpef_ap_confronto", placeholder="Lascia vuoto finché non scegli lo scenario",
        )
    with c2:
        testo_fondo = st.text_input(
            "Fondo pensione (€) · scenario",
            key="irpef_fondo_confronto", placeholder="Lascia vuoto finché non scegli lo scenario",
        )
    st.caption("Puoi modificare i due importi soltanto per confrontare le formule: "
               "nessuna cifra viene salvata in Supabase. Per indicare uno zero effettivo, scrivi 0.")
    if not testo_ap.strip() or not testo_fondo.strip():
        st.info("Inserisci entrambi gli importi oppure premi il pulsante per usare i valori di prova del foglio.")
        return

    try:
        ap = importo_valido(testo_ap)
        fondo = importo_valido(testo_fondo)
        mandanti = elenco_mandanti(client)
        ricavi = leggi_fatturato(client, anno["id"])
        if not mandanti or not ricavi or any(r.get("notes") != NOTA_TEST for r in ricavi):
            st.info("Confronto sospeso: occorrono esclusivamente i fatturati di prova del foglio.")
            return
        risultati, _registrato, fatturato = riepilogo(mandanti, ricavi)
        if fatturato is None or any(r["mesi"] == 0 for r in risultati):
            st.info("Confronto sospeso: ogni mandante deve avere almeno un mese compilato.")
            return
        _dettagli, enasarco, mono = calcola_confronto(
            mandanti, ricavi,
            D(str(presenti["enasarco_tasso_foglio"]["value"])),
            D(str(presenti["enasarco_massimale_pluri"]["value"])),
        )
        if mono:
            st.info("Mandante monomandataria presente: concordiamo prima la formula Enasarco.")
            return
        costi, mancanti, non_test = calcola_riepilogo(client, anno["id"])
        if non_test or mancanti or len(costi) != len(VOCI_COSTI_TEST) or not _nessun_altro_costo(client, anno["id"]):
            st.info("Confronto sospeso: servono esattamente i sette costi di prova, senza altre spese.")
            return
        impostazioni = (client.table("vehicle_year_settings")
                        .select("vehicle_id,annual_km_limit,excess_km_penalty")
                        .eq("fiscal_year_id", anno["id"]).execute()).data or []
        km = (client.table("vehicle_monthly")
              .select("vehicle_id,month,distance_km")
              .eq("fiscal_year_id", anno["id"]).execute()).data or []
        penale = _penale(impostazioni, km)
        if penale is not None and penale != 0:
            st.info("Penale chilometrica diversa da zero: prima concordiamo la sua inclusione nei costi.")
            return
        deducibili = sum((r["Deducibile"] for r in costi), D("0"))
        p = {codice: D(str(presenti[codice]["value"])) for codice in PARAMETRI}
        imponibile, irpef, veneto, verona, totale = calcola_irpef_foglio(
            fatturato, deducibili, enasarco, ap, p["inps_fisso_foglio"], fondo,
            p["irpef_aliquota_1_foglio"], p["irpef_soglia_2_foglio"],
            p["irpef_aliquota_2_foglio"], p["irpef_soglia_3_foglio"],
            p["irpef_aliquota_3_foglio"], p["addizionale_veneto_foglio"],
            p["addizionale_verona_foglio"],
        )
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Impossibile costruire il confronto IRPEF: nessun dato modificato.")
        return

    st.dataframe([
        {"Passaggio": "Fatturato stimato INVARIATO", "Importo": _valuta(fatturato), "Riferimento": "Conto economico!B1"},
        {"Passaggio": "Costi deducibili di prova", "Importo": _valuta(deducibili), "Riferimento": "Costi!F14"},
        {"Passaggio": "Enasarco separato (formula imponibile)", "Importo": _valuta(enasarco), "Riferimento": "Imposte!E4"},
        {"Passaggio": "Contributi A.P. · scenario NON registrato", "Importo": _valuta(ap), "Riferimento": "Imposte!B3"},
        {"Passaggio": "INPS fisso del foglio", "Importo": _valuta(p["inps_fisso_foglio"]), "Riferimento": "Imposte!B5"},
        {"Passaggio": "Fondo pensione · scenario NON registrato", "Importo": _valuta(fondo), "Riferimento": "Detrazioni e deduzioni!I3"},
        {"Passaggio": "1 · Imponibile IRPEF del foglio", "Importo": _valuta(imponibile), "Riferimento": "Conto economico!B9"},
        {"Passaggio": "2 · IRPEF a scaglioni del foglio", "Importo": _valuta(irpef), "Riferimento": "Imposte!B7"},
        {"Passaggio": "3 · Addizionale Veneto del foglio", "Importo": _valuta(veneto), "Riferimento": "Imposte!B8"},
        {"Passaggio": "3 · Addizionale Verona del foglio", "Importo": _valuta(verona), "Riferimento": "Imposte!B9"},
        {"Passaggio": "Totale IRPEF e addizionali (solo somma)", "Importo": _valuta(totale), "Riferimento": "Conto economico!B14"},
    ], hide_index=True, use_container_width=True)
    st.caption("Formula del foglio: fatturato − costi deducibili − Enasarco − contributi A.P. "
               "− INPS fisso − fondo pensione. L'Enasarco NON è sottratto dal fatturato registrato: "
               "entra solo nella formula dell'imponibile.")
    if (ap == D("8000") and fondo == D("5300") and
            all(p[chiave] == valore for chiave, valore in (
                ("enasarco_tasso_foglio", D("0.085")),
                ("enasarco_massimale_pluri", D("30057")),
                ("inps_fisso_foglio", D("4611.64")),
                ("irpef_aliquota_1_foglio", D("0.23")),
                ("irpef_soglia_2_foglio", D("28000")),
                ("irpef_aliquota_2_foglio", D("0.33")),
                ("irpef_soglia_3_foglio", D("50000")),
                ("irpef_aliquota_3_foglio", D("0.43")),
                ("addizionale_veneto_foglio", D("0.0123")),
                ("addizionale_verona_foglio", D("0.008")),
            ))):
        attesi = (D("82033.56"), D("27474.43"), D("1009.01"), D("656.27"), D("29139.71"))
        if all(val.quantize(CENT, rounding=ROUND_HALF_UP) == atteso
               for val, atteso in zip((imponibile, irpef, veneto, verona, totale), attesi)):
            st.success("Confronto matematico: imponibile, IRPEF e addizionali coincidono con il foglio.")
        else:
            st.warning("I valori differiscono dal foglio di prova: verifica i dati a monte.")
    st.warning("Solo confronto del foglio: NON usare questi numeri come imposte da pagare o "
               "come netto mensile. Le somme realmente versate e le deduzioni ammesse "
               "vanno registrate e verificate separatamente.")
