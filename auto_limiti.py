"""Confronto dei chilometri con il limite contrattuale; prove distinte."""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _chilometri, _veicoli
from fatturato import euro

# Marcatore storico da conservare per rileggere i dati esistenti.
NOTA_LIMITE_TEST = "DATI DI PROVA - limite chilometrico e penale del foglio originale"
CENT = Decimal("0.01")


def calcola_sforamento(chilometri: Decimal, limite: Decimal, tariffa: Decimal) -> tuple[Decimal, Decimal]:
    """Restituisce differenza con segno e penale non negativa."""
    differenza = chilometri - limite
    penale = max(differenza, Decimal("0")) * tariffa
    return differenza, penale.quantize(CENT, rounding=ROUND_HALF_UP)


def _leggi_impostazioni(client: Client, anno_id: str, veicolo_id: str) -> dict | None:
    risposta = (client.table("vehicle_year_settings")
                .select("id,annual_km_limit,excess_km_penalty,notes")
                .eq("fiscal_year_id", anno_id).eq("vehicle_id", veicolo_id)
                .limit(1).execute())
    return risposta.data[0] if risposta.data else None


def mostra_limiti_auto(client: Client, anno: dict) -> None:
    veicolo_id = st.session_state.get("auto_veicolo")
    if not veicolo_id:
        return
    st.divider()
    st.subheader("Auto · limite chilometrico e penale")
    st.caption("Confronto contrattuale; non costituisce un calcolo fiscale.")
    try:
        veicolo = next((item for item in _veicoli(client) if item["id"] == veicolo_id), None)
        if veicolo is None:
            st.info("Seleziona un veicolo nella sezione Percorrenza.")
            return
        impostazioni = _leggi_impostazioni(client, anno["id"], veicolo_id)
    except Exception:
        st.error("Impossibile leggere il limite chilometrico: nessun dato modificato.")
        return
    if impostazioni is None:
        st.info("Nessun limite chilometrico registrato per questo veicolo e questo anno.")
        if anno["status"] == "open" and veicolo.get("notes") == NOTA_VEICOLO_TEST:
            st.caption("Valori dimostrativi: limite 50.000 km; penale 0,16 € per km eccedente.")
            if st.button("Carica limite e penale di prova", key="auto_carica_limiti"):
                try:
                    if _leggi_impostazioni(client, anno["id"], veicolo_id) is not None:
                        raise ValueError("Impostazioni già presenti: nessun valore sovrascritto.")
                    risposta = client.table("vehicle_year_settings").insert({
                        "fiscal_year_id": anno["id"], "vehicle_id": veicolo_id,
                        "annual_km_limit": 50000, "excess_km_penalty": "0.16",
                        "notes": NOTA_LIMITE_TEST,
                    }).execute()
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Inserimento non confermato")
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("Inserimento non confermato: verifica la sezione prima di riprovare.")
                else:
                    st.rerun()
        return
    if impostazioni.get("notes") == NOTA_LIMITE_TEST:
        st.warning("PARAMETRI DI PROVA: limite e penale non verificati sul contratto attuale.")
    if impostazioni["annual_km_limit"] is None or impostazioni["excess_km_penalty"] is None:
        st.info("Limite o penale non impostati: nessun confronto calcolato.")
        return
    limite = Decimal(str(impostazioni["annual_km_limit"]))
    tariffa = Decimal(str(impostazioni["excess_km_penalty"]))
    try:
        righe = _chilometri(client, anno["id"], veicolo_id)
    except Exception:
        st.error("Impossibile leggere i chilometri: nessun dato modificato.")
        return
    valori = [Decimal(str(r["distance_km"])) for r in righe]
    reale = sum(valori, Decimal("0"))
    stimato = reale / len(valori) * 12 if valori else None
    differenza_reale, penale_reale = calcola_sforamento(reale, limite, tariffa)
    col1, col2 = st.columns(2)
    col1.metric("Limite annuo", f"{limite:,.0f}".replace(",", ".") + " km")
    col2.metric("Penale per km eccedente", euro(tariffa))
    st.write(f"**Differenza chilometri registrati − limite:** {differenza_reale:,.0f} km".replace(",", "."))
    st.write(f"**Penale sui chilometri registrati:** {euro(penale_reale)}")
    if stimato is not None:
        differenza_stimata, penale_stimata = calcola_sforamento(stimato, limite, tariffa)
        st.write(f"**Differenza chilometri stimati − limite:** {differenza_stimata:,.0f} km".replace(",", "."))
        st.write(f"**Penale sui chilometri stimati:** {euro(penale_stimata)}")
    else:
        st.caption("Nessuna stima: non ci sono mesi di percorrenza compilati.")
    st.caption("Una differenza negativa indica chilometri ancora disponibili. La penale è zero finché il limite non viene superato.")
    if anno["status"] == "open" and impostazioni.get("notes") == NOTA_LIMITE_TEST:
        with st.expander("Elimina limite e penale di prova"):
            conferma = st.checkbox("Confermo l'eliminazione dei parametri di prova", key="auto_limiti_conferma")
            if st.button("Elimina limite e penale di prova", disabled=not conferma, key="auto_limiti_elimina"):
                try:
                    risposta = (client.table("vehicle_year_settings").delete()
                                .eq("id", impostazioni["id"])
                                .eq("fiscal_year_id", anno["id"])
                                .eq("vehicle_id", veicolo_id)
                                .eq("notes", NOTA_LIMITE_TEST).execute())
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Eliminazione non confermata: verifica la sezione prima di riprovare.")
                else:
                    st.rerun()
