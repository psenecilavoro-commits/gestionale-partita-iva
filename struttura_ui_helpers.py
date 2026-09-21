import streamlit as st


def errore_scrittura(exc):
    if isinstance(exc, ValueError):
        st.warning(str(exc))
    else:
        st.error("Operazione non confermata: ricarica il registro prima di riprovare. Un dato collegato va prima scollegato.")
