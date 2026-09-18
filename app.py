"""Punto di ingresso del Gestionale Partita IVA."""

import streamlit as st
from supabase import create_client

from auth import current_user, get_client, sign_in, sign_out

st.set_page_config(page_title="Gestionale Partita IVA", page_icon="📊", layout="wide")

st.title("Gestionale Partita IVA")
st.caption("Versione iniziale · applicazione desktop")

try:
    get_client()
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

st.success("Accesso a Supabase riuscito.")
st.info("Prima di inserire dati fiscali, verifichiamo i permessi del database.")

if st.button("Verifica accesso al database", type="primary"):
    # Lettura limitata, senza visualizzare né modificare dati esistenti.
    try:
        get_client().table("fiscal_years").select("id").limit(1).execute()
    except Exception:
        st.error("Accesso autenticato: verifica non riuscita. Nessun dato è stato modificato.")
    else:
        st.success("Accesso autenticato: lettura consentita.")

    # Un client NUOVO, privo di login, deve ricevere un errore di permessi.
    # Una risposta vuota ma riuscita non dimostra che i privilegi siano negati.
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

st.caption("Questa verifica è in sola lettura. Non prova ancora l'isolamento tra utenti diversi.")
