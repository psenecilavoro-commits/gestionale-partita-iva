"""Parametri di scenario distinti da regole fiscali confermate.

Nessun parametro viene creato automaticamente all'apertura. Le tre famiglie
sono caricabili su richiesta, restano PROVVISORIE e modificabili. Nessun
risultato qui calcolato viene utilizzato come netto, debito o contributo.
"""
from decimal import Decimal, InvalidOperation

import streamlit as st
from supabase import Client

from fatturato import euro
from imposte_enasarco import mostra_confronto_enasarco
from imposte_inps import mostra_confronto_inps
from imposte_irpef import mostra_confronto_irpef

D = Decimal
# Valori e riferimenti conservati soltanto come metadati tecnici per i test.
GRUPPI = (
    ("Enasarco", (
        ("enasarco_tasso_foglio", "Aliquota quota personale · scenario", "0.085", "RATE", "Fatturato!B19/E19/H19/K19"),
        ("enasarco_massimale_pluri", "Massimale plurimandatario · riferimento 2026 provvisorio", "30478", "EUR", "Imposte!E1"),
        ("enasarco_massimale_mono", "Massimale monomandatario · riferimento 2026 provvisorio", "45717", "EUR", "Imposte!E2"),
    )),
    ("INPS", (
        ("inps_fisso_foglio", "INPS fisso · scenario", "4611.64", "EUR", "Imposte!B5"),
        ("inps_minimale_foglio", "Minimale · riferimento 2026 provvisorio", "18808", "EUR", "Imposte!E6"),
        ("inps_aliquota_prima_foglio", "Aliquota prima fascia · scenario", "0.2448", "RATE", "Imposte!F6"),
        ("inps_soglia_seconda_foglio", "Soglia seconda fascia · scenario", "56224", "EUR", "Imposte!E7"),
        ("inps_aliquota_seconda_foglio", "Aliquota seconda fascia · scenario", "0.2548", "RATE", "Imposte!F7"),
        ("inps_massimale_foglio", "Massimale · scenario, da aggiornare", "122295", "EUR", "Imposte!E8"),
    )),
    ("Deduzione forfettaria agenti", (
        ("agenti_soglia_1_foglio", "Prima soglia · modello definitivo", "6197.48", "EUR", "Imposte!E16"),
        ("agenti_aliquota_1_foglio", "Aliquota prima fascia · modello definitivo", "0.03", "RATE", "Imposte!F16"),
        ("agenti_soglia_2_foglio", "Seconda soglia · modello definitivo", "77468.53", "EUR", "Imposte!E17"),
        ("agenti_aliquota_2_foglio", "Aliquota seconda fascia · modello definitivo", "0.01", "RATE", "Imposte!F17"),
        ("agenti_soglia_3_foglio", "Terza soglia · modello definitivo", "92962.24", "EUR", "Imposte!E18"),
        ("agenti_aliquota_3_foglio", "Aliquota terza fascia · modello definitivo", "0.005", "RATE", "Imposte!F18"),
    )),
    ("IRPEF e addizionali", (
        ("irpef_aliquota_1_foglio", "Aliquota prima fascia · scenario", "0.23", "RATE", "Imposte!F10"),
        ("irpef_soglia_2_foglio", "Soglia seconda fascia · scenario", "28000", "EUR", "Imposte!E11"),
        ("irpef_aliquota_2_foglio", "Aliquota seconda fascia · scenario", "0.33", "RATE", "Imposte!F11"),
        ("irpef_soglia_3_foglio", "Soglia terza fascia · scenario", "50000", "EUR", "Imposte!E12"),
        ("irpef_aliquota_3_foglio", "Aliquota terza fascia · scenario", "0.43", "RATE", "Imposte!F12"),
        ("addizionale_veneto_foglio", "Addizionale Veneto · scenario", "0.0123", "RATE", "Imposte!F13"),
        ("addizionale_verona_foglio", "Addizionale Verona · scenario", "0.008", "RATE", "Imposte!F14"),
    )),
)


def _formato(valore: str | Decimal, unita: str) -> str:
    numero = D(str(valore))
    if unita == "RATE":
        return f"{(numero * 100):,.4f}".replace(",", "§").replace(".", ",").replace("§", ".").rstrip("0").rstrip(",") + "%"
    return euro(numero)


def _numero(testo: str, unita: str) -> Decimal:
    pulito = testo.strip().replace(" ", "")
    if not pulito:
        raise ValueError("Inserisci un numero, usando 0 solo se voluto.")
    if "," in pulito:
        pulito = pulito.replace(".", "").replace(",", ".")
    try:
        valore = D(pulito)
    except InvalidOperation as exc:
        raise ValueError("Importo non valido: usa ad esempio 30057 oppure 0,085.") from exc
    if not valore.is_finite() or valore < 0 or (unita == "RATE" and valore > 2):
        raise ValueError("Il valore deve essere non negativo e, per le aliquote, al massimo 2.")
    if valore.as_tuple().exponent < -6 or len(valore.as_tuple().digits) > 18:
        raise ValueError("Il database accetta al massimo sei decimali e 18 cifre complessive.")
    return valore


def _leggi(client: Client, anno_id: str) -> dict[str, dict]:
    risposta = (
        client.table("fiscal_parameters")
        .select("id,code,description,value,unit,source,source_date,is_provisional")
        .eq("fiscal_year_id", anno_id)
        .execute()
    )
    return {r["code"]: r for r in (risposta.data or [])}


def _carica_gruppo(client: Client, anno_id: str, voci: tuple, presenti: dict) -> int:
    """Carica soltanto le voci assenti; preserva i valori esistenti."""
    nuovi = [{
        "fiscal_year_id": anno_id,
        "code": codice,
        "description": descrizione,
        "value": valore,
        "unit": unita,
        "source": "CONFRONTO NON VERIFICATO: foglio originale " + cella,
        "is_provisional": True,
    } for codice, descrizione, valore, unita, cella in voci if codice not in presenti]
    if not nuovi:
        return 0
    risposta = client.table("fiscal_parameters").insert(nuovi).execute()
    if len(risposta.data or []) != len(nuovi):
        raise RuntimeError("Inserimento non confermato")
    return len(nuovi)


def _modifica(client: Client, anno_id: str, riga: dict, valore: Decimal) -> None:
    risposta = (
        client.table("fiscal_parameters")
        .update({
            "value": str(valore),
            "is_provisional": True,
            "source": "VALORE MODIFICATO MANUALMENTE; da verificare prima dei calcoli",
            "source_date": None,
        })
        .eq("id", riga["id"])
        .eq("fiscal_year_id", anno_id)
        .eq("code", riga["code"])
        .execute()
    )
    if len(risposta.data or []) != 1:
        raise RuntimeError("Modifica non confermata")


def mostra_imposte(client: Client, anno: dict) -> None:
    st.subheader("Imposte · parametri")
    st.warning("PARAMETRI PROVVISORI: aliquote, soglie, massimali e detrazioni devono "
               "essere verificati per l'anno fiscale selezionato. Non sono importi da versare.")
    st.info("L'Enasarco personale non riduce il fatturato registrato. Provvigioni, "
            "trattenute, importo delle fatture e imponibile IVA restano distinti.")
    st.caption("Tre gruppi configurabili. I valori iniziali sono soltanto esempi di calcolo "
               "e sono salvati unicamente su tua richiesta.")
    try:
        presenti = _leggi(client, anno["id"])
    except Exception:
        st.error("Impossibile leggere i parametri: nessun dato modificato.")
        return
    for nome_gruppo, voci in GRUPPI:
        st.markdown(f"### {nome_gruppo}")
        st.dataframe([{
            "Parametro": descrizione,
            "Valore di prova": _formato(valore, unita),
            "Valore configurato": _formato(presenti[codice]["value"], presenti[codice]["unit"])
            if codice in presenti else "—",
        } for codice, descrizione, valore, unita, _cella in voci],
            hide_index=True, width="stretch")
        if nome_gruppo == "INPS":
            st.caption("Minimale, soglia, aliquote e massimale sono riferimenti 2026 usati provvisoriamente per il 2027. "
                       "I contributi di anni precedenti si deducono solo se effettivamente pagati nell'anno selezionato.")
        if nome_gruppo == "Enasarco":
            st.caption("L'8,5% è la quota personale del modello. I massimali 30.478 € / 45.717 € sono riferimenti 2026 "
                       "provvisori per il 2027 e restano modificabili per anno.")
        if anno["status"] != "open":
            continue
        mancanti = [v for v in voci if v[0] not in presenti]
        if mancanti:
            if st.button(f"Carica i parametri di prova · {nome_gruppo}", key=f"imposte_carica_{voci[0][0]}"):
                try:
                    _carica_gruppo(client, anno["id"], voci, presenti)
                except Exception:
                    st.error("Caricamento non confermato: aggiorna e controlla i valori prima di riprovare.")
                else:
                    st.rerun()
        modificabili = [v for v in voci if v[0] in presenti]
        if modificabili:
            with st.expander(f"Modifica un parametro · {nome_gruppo}"):
                dizionario = {v[0]: v for v in modificabili}
                selezione = st.selectbox("Parametro", list(dizionario),
                                         format_func=lambda codice: dizionario[codice][1],
                                         key=f"imposte_scelta_{voci[0][0]}")
                record = presenti[selezione]
                with st.form(f"imposte_modifica_{selezione}"):
                    testo = st.text_input(
                        "Nuovo valore (aliquote in forma decimale: 0,085 = 8,5%)",
                        value=str(record["value"]).replace(".", ","),
                        help="Puoi modificare il parametro. Resterà provvisorio.",
                    )
                    conferma = st.form_submit_button("Salva parametro")
                if conferma:
                    try:
                        valore = _numero(testo, record["unit"])
                        _modifica(client, anno["id"], record, valore)
                    except ValueError as exc:
                        st.warning(str(exc))
                    except Exception:
                        st.error("Modifica non confermata: verifica la tabella prima di riprovare.")
                    else:
                        st.rerun()
    if anno["status"] != "open":
        st.info("Anno chiuso: parametri in sola lettura.")
    mostra_confronto_enasarco(client, anno, presenti)
    mostra_confronto_inps(client, anno, presenti)
    mostra_confronto_irpef(client, anno, presenti)
    st.caption("Per un utilizzo fiscale effettivo occorrono parametri aggiornati, "
               "versamenti documentati, deduzioni e detrazioni verificate e documenti IVA completi.")
