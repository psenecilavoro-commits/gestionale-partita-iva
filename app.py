"""Punto di ingresso del Gestionale Partita IVA."""

import streamlit as st

from auth import current_user, get_client, sign_in, sign_out

st.set_page_config(page_title="Gestionale Partita IVA", page_icon="📊", layout="wide")

st.title("Gestionale Partita IVA")
st.caption("Versione iniziale · applicazione desktop")

# Non mostrare contenuti protetti se il collegamento non è configurato.
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
                # Non mostrare errori tecnici che potrebbero esporre dettagli del servizio.
                st.error("Accesso non riuscito. Controlla le credenziali e riprova.")
    st.stop()

with st.sidebar:
    st.caption("Utente autenticato")
    st.write(user.email or "Account Supabase")
    if st.button("Esci"):
        sign_out()
        st.rerun()

st.success("Accesso a Supabase riuscito.")
st.info(
    "Il login è attivo. Le schermate fiscali saranno aggiunte dopo la verifica "
    "del funzionamento delle policy RLS. Nessun dato fiscale viene ancora letto."
)
