"""Confronto IVA mensile: fatturato al 22% e registro acquisti separato.

Nessuna liquidazione ufficiale: vendite, crediti, note di credito, opzioni
fiscali e completezza dei documenti devono ancora essere verificati.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import MESI, NOTA_TEST, euro, leggi_fatturato

D = Decimal
CENT = D("0.01")
ALIQUOTA_FOGLIO = D("0.22")


def periodo_detrazione(operazione: date, ricezione: date, registrazione: date) -> tuple[int, int, bool]:
    """Prima imputazione mensile simulata, con retrodatazione facoltativa.

    Presuppone fattura ordinaria, IVA detraibile e registrazione regolare;
    casistiche speciali, rettifiche, decadenze e liquidazione trimestrale fuori ambito.
    """
    if not isinstance(operazione, date) or not isinstance(ricezione, date) or not isinstance(registrazione, date):
        raise ValueError("Inserisci tre date valide.")
    if ricezione < operazione or registrazione < ricezione:
        raise ValueError("In questo confronto ricezione e registrazione devono seguire l'operazione in ordine cronologico.")
    if (ricezione.year == operazione.year and ricezione.month == operazione.month
            and registrazione.year == operazione.year and registrazione.month == operazione.month):
        return operazione.year, operazione.month, False
    # Il mese dell'operazione si può scegliere se fattura ricevuta e annotata
    # entro il giorno 15 del mese dopo, ma non per operazioni dell'anno prima.
    if operazione.month < 12:
        mese_dopo = date(operazione.year, operazione.month + 1, 15)
        if ricezione <= mese_dopo and registrazione <= mese_dopo:
            return operazione.year, operazione.month, True
    return registrazione.year, registrazione.month, False


def iva_vendite_foglio(fatturati: list[dict]) -> dict[int, D]:
    """Confronto G2:G13, non documento fiscale: solo mesi espressi nel DB."""
    imponibili: dict[int, D] = {}
    for riga in fatturati:
        mese = int(riga["month"])
        valore = D(str(riga["amount"]))
        if mese not in range(1, 13) or not valore.is_finite() or valore < 0:
            raise ValueError("Fatturato mensile non valido.")
        imponibili[mese] = imponibili.get(mese, D("0")) + valore
    return {mese: (imponibile * ALIQUOTA_FOGLIO).quantize(CENT, rounding=ROUND_HALF_UP)
            for mese, imponibile in imponibili.items()}


def mostra_anteprima_iva(client: Client, anno: dict) -> None:
    # Import a runtime: iva_acquisti usa la funzione pura periodo_detrazione.
    from iva_acquisti import leggi_fatture_iva, mostra_registro_iva_acquisti, riepilogo_acquisti_iva

    anno_num = int(anno["fiscal_year"])
    st.divider()
    st.subheader("IVA mensile · confronto e verifica date")
    st.warning("Anteprima matematica, NON liquidazione IVA: il 22% deriva dal foglio "
               "e non verifica aliquote delle singole fatture, imponibilità o note di credito. "
               "I documenti di acquisto registrati possono essere incompleti; "
               "crediti precedenti, rettifiche e periodicità non sono conteggiati.")
    try:
        fatturati = leggi_fatturato(client, anno["id"])
        output = iva_vendite_foglio(fatturati)
    except (ValueError, ArithmeticError):
        st.error("Fatturati non validi per il confronto IVA. Nessun dato modificato.")
        return
    except Exception:
        st.error("Impossibile leggere il fatturato. Nessun dato modificato.")
        return
    if any(r.get("notes") == NOTA_TEST for r in fatturati):
        st.warning("Sono presenti fatturati di PROVA: anche i valori IVA del confronto sono simulati.")
    try:
        acquisti = riepilogo_acquisti_iva(leggi_fatture_iva(client, anno["id"]), anno_num)
    except Exception:
        acquisti = {}
        st.caption("Registro IVA acquisti non ancora disponibile o da verificare: "
                   "controlla la sezione dedicata qui sotto.")

    st.dataframe([{
        "Mese": nome,
        "IVA fatturata · 22% del foglio · TEST": euro(output[mese]) if mese in output else "—",
        "IVA detraibile auto · registrata": euro(acquisti[mese]["auto"]) if mese in acquisti else "—",
        "Altra IVA detraibile · registrata": euro(acquisti[mese]["altro"]) if mese in acquisti else "—",
        "IVA dovuta": "— · non determinata",
    } for mese, nome in enumerate(MESI, 1)], hide_index=True, use_container_width=True)
    st.caption("Un mese privo di documenti non equivale a 0. IVA sulle vendite = simulazione "
               "dal fatturato, IVA sugli acquisti = quote documentate e da te confermate. "
               "Non sottrarre i due valori come liquidazione effettiva.")

    with st.expander("Verifica il periodo di una fattura d'acquisto · senza salvataggio"):
        st.caption("Solo fattura ordinaria con IVA effettivamente detraibile e liquidazione mensile. "
                   "La detrazione per il mese dell'operazione è una possibilità, non un obbligo. "
                   "La fattura di dicembre ricevuta a gennaio non torna nella liquidazione di dicembre.")
        with st.form(f"iva_date_form_{anno['id']}"):
            operazione = st.date_input("Data dell'operazione", value=date(anno_num, 1, 1),
                                      key=f"iva_operazione_{anno['id']}")
            ricezione = st.date_input("Data di ricezione della fattura", value=date(anno_num, 1, 1),
                                     key=f"iva_ricezione_{anno['id']}")
            registrazione = st.date_input("Data di registrazione della fattura", value=date(anno_num, 1, 1),
                                         key=f"iva_registrazione_{anno['id']}")
            verifica = st.form_submit_button("Verifica il periodo (non salva)")
        if verifica:
            try:
                anno_iva, mese_iva, retro = periodo_detrazione(operazione, ricezione, registrazione)
            except ValueError as exc:
                st.warning(str(exc))
            else:
                descrizione = f"{MESI[mese_iva - 1]} {anno_iva}"
                if retro:
                    st.success(f"Con le ipotesi indicate, la detrazione può essere anticipata a {descrizione}.")
                else:
                    st.info(f"Primo periodo mensile indicativo: {descrizione}. "
                            "Non è stata applicata la retrodatazione del mese precedente.")
                if anno_iva != anno_num:
                    st.warning(f"Il periodo risulta nell'anno {anno_iva}, diverso dall'anno visualizzato {anno_num}.")
        st.caption("In assenza di una fattura reale e della verifica di detraibilità, "
                   "questo controllo non determina un credito IVA.")

    mostra_registro_iva_acquisti(client, anno)
