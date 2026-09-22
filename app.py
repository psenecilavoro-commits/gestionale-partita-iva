"""Punto di ingresso del Gestionale Partita IVA."""

from datetime import date

import streamlit as st

from accantonamenti_completi import mostra_accantonamenti
from accantonamenti_confronto import mostra_confronto_accantonamenti
from auth import current_user, get_client, sign_in, sign_out, reset_fiscal_inputs
from auto import prepara_auto_unica
from auto_riepilogo import mostra_riepilogo_auto
from auto_spese_reali import mostra_spese_auto
from conto_economico import mostra_conto_economico
from contributi_versati import mostra_contributi_versati
from costi_scheda import mostra_tabella_costi
from database import create_fiscal_year, get_fiscal_year
from fatture_acquisto_xml import mostra_importa_xml_acquisti
from fatture_provvigioni import mostra_carica_fatture
from sanitarie_unificate import mostra_detrazioni_unificate
from fatturato import mostra_fatturato
from imposte_parametri import mostra_imposte
from iva_anteprima import mostra_anteprima_iva
from mandanti import aggiungi_mandante, elenco_mandanti
from quadro_mensile import mostra_quadro_mensile
from registrazioni_reali import mostra_costi_reali
from riepilogo_laterale import mostra_base
from stile import applica_stile
from struttura_ui import (mostra_vendite, mostra_periodi_iva, mostra_pensione,
                          mostra_conto_registrato, mostra_riconciliazione)

st.set_page_config(page_title="Gestionale Partita IVA", page_icon="📊", layout="wide",
                   initial_sidebar_state="expanded")
applica_stile()
st.title("Gestionale Partita IVA")

try:
    client = get_client()
except Exception:
    st.error("Collegamento a Supabase non disponibile. Controlla i Secrets dell'app su Streamlit.")
    st.stop()

user = current_user()
if user is None:
    st.subheader("Accedi")
    st.write("Inserisci l'email e la password dell'utente creato in Supabase.")
    with st.form("login", clear_on_submit=True):
        email = st.text_input("Email", placeholder="nome@esempio.it")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Accedi", type="primary")
    if submitted:
        if not email.strip() or not password:
            st.warning("Inserisci email e password.")
        else:
            try:
                sign_in(email, password)
                st.rerun()
            except Exception:
                st.error("Accesso non riuscito. Controlla le credenziali e riprova.")
    st.stop()

with st.sidebar:
    st.caption("Utente autenticato")
    st.write(user.email or "Account Supabase")
    if st.button("Esci"):
        sign_out()
        st.rerun()
    st.divider()
    # Il placeholder resta in alto e viene aggiornato quando cambia lo scenario.
    conto_slot = st.empty()

st.subheader("Anno fiscale")
# Il selettore propone l'anno corrente dal 2027, senza modificare anni storici.
anni = list(range(2027, 2051))
anno_corrente = min(max(date.today().year, 2027), anni[-1])
anno_selezionato = st.selectbox("Anno da visualizzare", anni,
                               index=anni.index(anno_corrente), key="anno_fiscale_selezionato",
                               on_change=reset_fiscal_inputs)
try:
    fiscal_year = get_fiscal_year(client, anno_selezionato)
except Exception:
    st.error("Impossibile leggere l'anno fiscale dal database. Nessuna modifica effettuata.")
    st.stop()

if fiscal_year is None:
    st.write(f"L'anno {anno_selezionato} non è ancora presente. "
             "Puoi crearlo per registrare i dati di quell'anno; le detrazioni pluriennali già salvate resteranno disponibili.")
    if st.button(f"Crea anno fiscale {anno_selezionato}", type="primary"):
        try:
            create_fiscal_year(client, anno_selezionato)
        except Exception:
            try:
                already_created = get_fiscal_year(client, anno_selezionato)
            except Exception:
                already_created = None
            if already_created is not None:
                st.rerun()
            st.error("Non è stato possibile creare l'anno fiscale. Non ripetere il clic: comunicami questo messaggio.")
        else:
            st.rerun()
    st.stop()

st.success(f"Anno {fiscal_year['fiscal_year']} presente · stato: {fiscal_year['status']}.")
mostra_base(client, fiscal_year, conto_slot)

(
    scheda_fatturato,
    scheda_costi,
    scheda_auto,
    scheda_accantonamenti,
    scheda_conto_economico,
    scheda_imposte,
    scheda_detrazioni,
) = st.tabs([
    "Fatturato",
    "Costi",
    "Auto",
    "Tabella accantonamenti",
    "Conto economico",
    "Imposte",
    "Detrazioni e deduzioni",
])

with scheda_fatturato:
    # Carichiamo prima le mandanti perché servono al fatturato, ma mostriamo
    # la loro anagrafica per ultima, secondo l'ordine richiesto nella scheda.
    try:
        mandanti = elenco_mandanti(client)
    except Exception:
        st.error("Impossibile leggere le mandanti. Nessuna modifica effettuata.")
        st.stop()

    mostra_fatturato(client, fiscal_year, mandanti)
    mostra_vendite(client, fiscal_year)

    st.subheader("Mandanti")
    st.caption("Anagrafica delle mandanti associate alle registrazioni del fatturato.")
    if mandanti:
        st.dataframe(
            [{
                "Mandante": item["name"],
                "Rapporto Enasarco": item["enasarco_relationship"],
                "Stato": "Attiva" if item["active"] else "Non attiva",
            } for item in mandanti],
            hide_index=True, width="stretch",
        )
    else:
        st.info("Non hai ancora registrato alcuna mandante.")

    if fiscal_year["status"] == "open":
        scelta = st.selectbox(
            "Nome della mandante",
            ["Innovagroup Caino", "Innovagroup Borgo", "Innovagroup Erbe",
             "Innovagroup Fontanella", "Altra mandante (inserimento manuale)"],
        )
        with st.form("nuova_mandante"):
            nome_personalizzato = (
                st.text_input("Nome della nuova mandante")
                if scelta == "Altra mandante (inserimento manuale)" else ""
            )
            rapporto = st.selectbox(
                "Tipo di rapporto Enasarco", ["plurimandatario", "monomandatario"],
                help="Controlla il tipo di rapporto prima di salvare.",
            )
            salva = st.form_submit_button("Aggiungi mandante", type="primary")
        if salva:
            nome = nome_personalizzato if scelta == "Altra mandante (inserimento manuale)" else scelta
            try:
                aggiungi_mandante(client, nome, rapporto)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Salvataggio non confermato. Controlla l'elenco prima di riprovare.")
            else:
                st.rerun()
    else:
        st.info("L'anno fiscale è chiuso: non è possibile aggiungere mandanti da questa schermata.")

with scheda_costi:
    mostra_tabella_costi(client, fiscal_year)
    mostra_costi_reali(client, fiscal_year)
    mostra_riconciliazione(client, fiscal_year)

with scheda_auto:
    prepara_auto_unica(client)
    mostra_spese_auto(client, fiscal_year)
    mostra_riepilogo_auto(client, fiscal_year)

with scheda_accantonamenti:
    mostra_accantonamenti(client, fiscal_year)
    mostra_carica_fatture(client, fiscal_year)
    mostra_confronto_accantonamenti(client, fiscal_year)
    mostra_anteprima_iva(client, fiscal_year)
    mostra_importa_xml_acquisti(client, fiscal_year)
    mostra_quadro_mensile(client, fiscal_year)
    mostra_periodi_iva(client, fiscal_year)

with scheda_conto_economico:
    mostra_conto_registrato(client, fiscal_year)
    mostra_conto_economico(client, fiscal_year, sidebar_slot=conto_slot)

with scheda_imposte:
    mostra_imposte(client, fiscal_year)
    mostra_contributi_versati(client, fiscal_year)

with scheda_detrazioni:
    mostra_detrazioni_unificate(client, fiscal_year)
    mostra_pensione(client, fiscal_year)
