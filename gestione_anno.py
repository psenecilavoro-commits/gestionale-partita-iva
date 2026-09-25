"""Controlli di chiusura/riapertura dell'anno fiscale nella sidebar."""

import streamlit as st

from auth import reset_fiscal_inputs
from database import set_fiscal_year_status


def mostra_gestione_anno(client, anno: dict) -> None:
    anno_num = int(anno["fiscal_year"])
    stato = anno["status"]

    with st.sidebar:
        st.divider()
        st.markdown("### Gestione anno fiscale")

        if stato == "open":
            st.caption(
                "La chiusura blocca le modifiche dell'anno selezionato. "
                "I dati restano consultabili."
            )
            conferma = st.checkbox(
                f"Confermo la chiusura dell'anno {anno_num}",
                key=f"chiusura_anno_conferma_{anno_num}",
            )
            premuto = st.button(
                "Chiusura anno fiscale",
                key=f"chiusura_anno_btn_{anno_num}",
                disabled=not conferma,
                width="stretch",
            )
            if premuto:
                try:
                    set_fiscal_year_status(client, anno, "closed")
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error(
                        "Chiusura non confermata dal database. "
                        "Se è la prima volta che usi questa funzione, esegui "
                        "SQL_CHIUSURA_ANNO.sql nel Supabase del Gestionale Partita IVA."
                    )
                else:
                    reset_fiscal_inputs()
                    st.rerun()

        elif stato == "closed":
            st.caption(
                f"Anno {anno_num} chiuso: le modifiche sono disabilitate."
            )
            conferma = st.checkbox(
                f"Confermo la riapertura dell'anno {anno_num}",
                key=f"riapertura_anno_conferma_{anno_num}",
            )
            premuto = st.button(
                "Riapri anno fiscale",
                key=f"riapertura_anno_btn_{anno_num}",
                disabled=not conferma,
                width="stretch",
            )
            if premuto:
                try:
                    set_fiscal_year_status(client, anno, "open")
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error(
                        "Riapertura non confermata dal database. "
                        "Verifica che SQL_CHIUSURA_ANNO.sql sia stato eseguito "
                        "nel Supabase del Gestionale Partita IVA."
                    )
                else:
                    reset_fiscal_inputs()
                    st.rerun()
        else:
            st.error("Stato dell'anno fiscale non riconosciuto.")
