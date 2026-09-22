"""Scheda Costi: riepilogo di tutte le voci, editor solo delle stime non auto.

Le registrazioni di carburante, autostrada e rate restano nel medesimo database
ma possono essere gestite esclusivamente nella scheda Auto.
"""
from decimal import Decimal

import streamlit as st
from supabase import Client

from costi_tabella import (VOCI, CONFIG, _leggi, _tabella, _nuova, _modifica,
                          _elimina, _euro)

# Non confondere le voci di sola lettura con quelle inseribili. Le voci Auto
# sono ancora presenti in VOCI e pertanto nella tabella complessiva.
SOLO_AUTO = frozenset({"rate_auto", "carburante", "autostrada"})


def voci_modificabili() -> list[tuple]:
    """Questa scheda modifica soltanto le stime annuali non riservate ad Auto."""
    return [voce for voce in VOCI if voce[2] == "annuale" and voce[0] not in SOLO_AUTO]


def mostra_tabella_costi(client: Client, anno: dict) -> None:
    st.subheader("Costi")
    st.caption("Riepilogo di tutte le spese. Carburante, autostrada e rate auto si "
               "registrano e modificano nella scheda Auto; qui restano visibili "
               "il registrato e la stima annua. Le altre voci sono stime annuali, "
               "non necessariamente spese sostenute.")
    try:
        categorie, stime, spese, _veicoli, impostazioni, km = _leggi(client, anno["id"])
        tabella, incompleti, origini = _tabella(categorie, stime, spese, impostazioni, km)
    except Exception:
        st.error("Impossibile leggere la tabella dei costi. Nessun dato modificato.")
        return
    if "TEST" in origini:
        st.warning("Sono presenti DATI DI PROVA: non rappresentano spese reali.")
    if "MANUALE" in origini:
        st.info("Gli importi inseriti utilizzano parametri iniziali non verificati per il 2027.")
    st.dataframe(tabella, hide_index=True, width="stretch")
    if incompleti:
        st.caption("I totali fiscali sono sospesi per voci da verificare: "
                   + ", ".join(sorted(incompleti)) + ".")
    st.caption("* Rate auto: la quota deducibile è calcolata solo per i dati "
               "dimostrativi. Il contratto effettivo andrà verificato. "
               "Assicurazione: premio senza IVA.")
    if anno["status"] != "open":
        st.info("Anno chiuso: costi in sola lettura.")
        return

    annuali = voci_modificabili()
    st.markdown("**Aggiungi una spesa o una stima**")
    st.caption("Per carburante, autostrada e rate auto utilizza la scheda Auto.")
    for inizio in range(0, len(annuali), 4):
        colonne = st.columns(4)
        for colonna, voce in zip(colonne, annuali[inizio:inizio + 4]):
            if colonna.button("＋ " + voce[1], key="costi_aggiungi_" + voce[0], width="stretch"):
                st.session_state["costi_voce_aggiungi"] = voce[0]
    codice = st.session_state.get("costi_voce_aggiungi")
    # Vale anche per un vecchio stato di sessione che puntava a carburante/rate.
    if codice in {voce[0] for voce in annuali}:
        voce = CONFIG[codice]
        categoria = categorie.get(codice)
        if categoria and categoria["id"] in stime:
            st.info(f"{voce[1]}: è già presente una stima. Utilizza «Modifica una spesa» sotto.")
        else:
            with st.form("costi_form_aggiungi_" + codice):
                st.write("Nuovo inserimento: **" + voce[1] + "**")
                importo = st.text_input("Importo lordo (€), IVA compresa se prevista",
                                        placeholder="es. 250,00")
                st.caption("Parametri iniziali da verificare. Non è una fattura elettronica né una registrazione IVA.")
                conferma = st.form_submit_button("Salva nuova voce", type="primary")
            if conferma:
                try:
                    _nuova(client, anno, codice, importo)
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("Salvataggio non confermato: verifica la tabella prima di riprovare.")
                else:
                    st.session_state.pop("costi_voce_aggiungi", None)
                    st.rerun()

    st.markdown("**Modifica una spesa già inserita**")
    modificabili = []
    for codice_voce, nome, _tipo, *_ in annuali:
        categoria = categorie.get(codice_voce)
        if categoria and categoria["id"] in stime:
            modificabili.append((nome, categoria, stime[categoria["id"]]))
    if not modificabili:
        st.caption("Non ci sono ancora stime modificabili in questa scheda.")
        return
    opzioni = list(range(len(modificabili)))
    scelta = st.selectbox("Seleziona la voce da modificare", opzioni,
                          format_func=lambda i: (
                              modificabili[i][0] + " · stima annua · " +
                              _euro(Decimal(str(modificabili[i][2]["estimated_gross_amount"])))),
                          key="costi_modifica_selezione")
    nome, categoria, riga = modificabili[scelta]
    valore = Decimal(str(riga["estimated_gross_amount"]))
    with st.form("costi_form_modifica_" + riga["id"]):
        nuovo_importo = st.text_input("Nuovo importo lordo (€)",
                                      value=f"{valore:.2f}".replace(".", ","))
        st.caption("La modifica conserva l'origine dei dati di prova; non cambia aliquote o altri record.")
        salva = st.form_submit_button("Salva modifica", type="primary")
    if salva:
        try:
            _modifica(client, anno, categoria, riga, "annuale", nuovo_importo)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Modifica non confermata: controlla la tabella prima di riprovare.")
        else:
            st.rerun()
    with st.expander("Elimina la voce selezionata"):
        eliminare = st.checkbox("Confermo l'eliminazione definitiva di questa singola voce",
                               key="costi_conferma_elimina_" + riga["id"])
        if st.button("Elimina voce", key="costi_elimina_" + riga["id"], disabled=not eliminare):
            try:
                _elimina(client, anno, categoria, riga, "annuale")
            except Exception:
                st.error("Eliminazione non confermata: controlla la tabella prima di riprovare.")
            else:
                st.rerun()
