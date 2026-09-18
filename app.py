"""Punto di ingresso del Gestionale Partita IVA.

Prima versione: schermata iniziale, senza accesso ai dati finché non viene
configurata e verificata l'autenticazione Supabase.
"""

import streamlit as st

st.set_page_config(page_title="Gestionale Partita IVA", page_icon="📊", layout="wide")
st.title("Gestionale Partita IVA")
st.caption("Versione iniziale · applicazione desktop")
st.info(
    "La struttura del progetto è pronta. "
    "L'accesso ai dati e i calcoli fiscali saranno attivati nei prossimi passaggi, "
    "dopo la verifica delle credenziali e delle protezioni del database."
)
