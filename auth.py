"""Autenticazione Supabase per una singola sessione Streamlit.

Non condividere mai il client autenticato tramite st.cache_resource o variabili
in modulo: ogni visitatore deve avere una sessione Supabase indipendente.
"""

import streamlit as st
from supabase import Client, create_client
import base64
import json

_CLIENT_KEY = "_partita_iva_supabase_client"


def reset_fiscal_inputs():
    """Non riutilizzare importi e conferme del precedente anno fiscale."""
    for key in list(st.session_state):
        if key not in (_CLIENT_KEY, "anno_fiscale_selezionato"):
            del st.session_state[key]


def get_client() -> Client:
    """Restituisce un client Supabase isolato nella sessione del visitatore."""
    if _CLIENT_KEY not in st.session_state:
        key = st.secrets["SUPABASE_PUBLISHABLE_KEY"]
        valida_chiave_pubblica(key)
        st.session_state[_CLIENT_KEY] = create_client(
            st.secrets["SUPABASE_URL"],
            key,
        )
    return st.session_state[_CLIENT_KEY]


def valida_chiave_pubblica(key):
    if key.startswith("sb_publishable_"):
        return
    try:
        payload = key.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        if claims.get("role") == "anon":
            return
    except (ValueError, IndexError, TypeError):
        pass
    raise ValueError("Configurare esclusivamente una chiave publishable o anon, mai service_role/secret.")


def current_user():
    """Verifica il token presso Supabase; nessun accesso se manca/non è valido."""
    client = st.session_state.get(_CLIENT_KEY)
    if client is None:
        return None
    try:
        result = client.auth.get_user()
        return result.user
    except Exception:
        st.session_state.clear()
        return None


def sign_in(email: str, password: str) -> None:
    """Accede con l'utente già creato in Supabase; non registra nuovi utenti."""
    result = get_client().auth.sign_in_with_password(
        {"email": email.strip(), "password": password}
    )
    if result.session is None or result.user is None:
        raise ValueError("Accesso non confermato")


def sign_out() -> None:
    """Revoca la sessione corrente, senza scollegare altri dispositivi."""
    client = st.session_state.pop(_CLIENT_KEY, None)
    st.session_state.clear()
    if client is not None:
        try:
            client.auth.sign_out({"scope": "local"})
        except Exception:
            # L'app rimuove comunque la sessione locale anche se la rete non risponde.
            pass
