"""Punto di ingresso del Gestionale Partita IVA."""

from datetime import date

import streamlit as st
from supabase import create_client

from accantonamenti import mostra_accantonamenti
from auth import current_user, get_client, sign_in, sign_out
from auto import mostra_auto
from auto_autostrada import mostra_autostrada
from auto_carburante import mostra_carburante
from auto_limiti import mostra_limiti_auto
from auto_rate import mostra_rate
from conto_economico import mostra_conto_economico
from contributi_versati import mostra_contributi_versati
from costi_tabella import mostra_tabella_costi
from database import create_fiscal_year, get_fiscal_year
from sanitarie_unificate import mostra_detrazioni_unificate
from fatturato import mostra_fatturato
from imposte_parametri import mostra_imposte
from mandanti import aggiungi_mandante, elenco_mandanti

st.set_page_config(page_title="Gestionale Partita IVA", page_icon="📊", layout="wide")

st.title("Gestionale Partita IVA")
st.caption("Versione iniziale · applicazione desktop")

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

st.subheader("Anno fiscale")
# La scelta dell'anno e' necessaria per mostrare la rata corretta senza
# aggiornare o eliminare record storici. Nel 2026 resta selezionato il 2027;
# dagli anni successivi si propone l'anno corrente, modificabile dall'utente.
anni = list(range(2027, 2051))
anno_corrente = min(max(date.today().year, 2027), anni[-1])
anno_selezionato = st.selectbox("Anno da visualizzare", anni,
                               index=anni.index(anno_corrente), key="anno_fiscale_selezionato")
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

# Costi e' la seconda scheda, come richiesto. Le altre sezioni mantengono
# i nomi del foglio di riferimento.
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
    st.subheader("Mandanti")
    st.caption("Le mandanti sono anagrafiche; gli importi fatturati si registrano qui sotto.")
    try:
        mandanti = elenco_mandanti(client)
    except Exception:
        st.error("Impossibile leggere le mandanti. Nessuna modifica effettuata.")
        st.stop()

    if mandanti:
        st.dataframe(
            [
                {
                    "Mandante": item["name"],
                    "Rapporto Enasarco": item["enasarco_relationship"],
                    "Stato": "Attiva" if item["active"] else "Non attiva",
                }
                for item in mandanti
            ],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("Non hai ancora registrato alcuna mandante.")

    if fiscal_year["status"] == "open":
        scelta = st.selectbox(
            "Nome della mandante",
            [
                "Innovagroup Caino",
                "Innovagroup Borgo",
                "Innovagroup Erbe",
                "Innovagroup Fontanella",
                "Altra mandante (inserimento manuale)",
            ],
        )
        with st.form("nuova_mandante"):
            nome_personalizzato = (
                st.text_input("Nome della nuova mandante")
                if scelta == "Altra mandante (inserimento manuale)"
                else ""
            )
            rapporto = st.selectbox(
                "Tipo di rapporto Enasarco",
                ["plurimandatario", "monomandatario"],
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

    mostra_fatturato(client, fiscal_year, mandanti)

with scheda_costi:
    mostra_tabella_costi(client, fiscal_year)

with scheda_auto:
    mostra_auto(client, fiscal_year)
    mostra_limiti_auto(client, fiscal_year)
    mostra_carburante(client, fiscal_year)
    mostra_autostrada(client, fiscal_year)
    mostra_rate(client, fiscal_year)

with scheda_accantonamenti:
    mostra_accantonamenti(client, fiscal_year)

with scheda_conto_economico:
    mostra_conto_economico(client, fiscal_year)

with scheda_imposte:
    mostra_imposte(client, fiscal_year)
    mostra_contributi_versati(client, fiscal_year)

with scheda_detrazioni:
    mostra_detrazioni_unificate(client, fiscal_year)

with st.sidebar:
    with st.expander("Diagnostica dei permessi (sola lettura)"):
        if st.button("Verifica accesso al database"):
            try:
                client.table("fiscal_years").select("id").limit(1).execute()
            except Exception:
                st.error("Accesso autenticato: lettura non riuscita. Nessuna modifica è stata effettuata.")
            else:
                st.success("Accesso autenticato: lettura consentita.")

            try:
                anonymous_client = create_client(
                    st.secrets["SUPABASE_URL"],
                    st.secrets["SUPABASE_PUBLISHABLE_KEY"],
                )
                anonymous_client.table("fiscal_years").select("id").limit(1).execute()
            except Exception as exc:
                if str(getattr(exc, "code", "")) == "42501":
                    st.success("Accesso anonimo: lettura negata per mancanza di permessi.")
                else:
                    st.warning("Accesso anonimo: verifica non conclusiva. Riporta soltanto questo messaggio.")
            else:
                st.warning("Accesso anonimo: richiesta accettata. Non inserire ancora dati fiscali.")
    st.caption("Verificato l'isolamento in lettura dell'anno fiscale fra due utenti; altre tabelle non ancora testate separatamente.")