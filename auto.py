"""Percorrenza mensile e proiezione; l'inserimento è nella maschera Auto unificata."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import MESI

# Marcatori storici: non modificarli, identificano i record dimostrativi esistenti.
NOTA_VEICOLO_TEST = "VEICOLO DI PROVA - foglio originale"
NOTA_KM_TEST = "DATI DI PROVA - gennaio del foglio originale"
NOME_TEST = "Veicolo di prova (foglio originale)"


def _veicoli(client: Client) -> list[dict]:
    from registri import leggi_tutti
    return leggi_tutti(client, "vehicles")


def _chilometri(client: Client, anno_id: str, veicolo_id: str) -> list[dict]:
    from registri import leggi_tutti
    return leggi_tutti(client, "vehicle_monthly", fiscal_year_id=anno_id, vehicle_id=veicolo_id)


def _km_validi(testo: str) -> Decimal:
    testo = testo.strip().replace(" ", "")
    if not testo:
        raise ValueError("Inserisci i chilometri; scrivi 0 solo per un mese realmente a zero.")
    if "," in testo:
        testo = testo.replace(".", "").replace(",", ".")
    try:
        valore = Decimal(testo)
    except InvalidOperation as exc:
        raise ValueError("Chilometri non validi: esempio 2000 oppure 2000,50.") from exc
    if not valore.is_finite() or valore < 0 or valore > Decimal("9999999999.99"):
        raise ValueError("Inserisci chilometri non negativi e finiti.")
    if valore != valore.quantize(Decimal("0.01")):
        raise ValueError("Inserisci al massimo due decimali.")
    return valore


def _formato_km(valore: Decimal) -> str:
    return f"{valore:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".") + " km"


def auto_unica(veicoli: list[dict]) -> dict | None:
    """Preferisce l'unica auto effettiva, conservando il veicolo demo separato.

    In presenza di più auto effettive non ne sceglie arbitrariamente una:
    sarebbe possibile attribuire spese e chilometri al veicolo sbagliato.
    """
    reali = [v for v in veicoli if v.get("notes") != NOTA_VEICOLO_TEST]
    if len(reali) > 1:
        raise ValueError("Risultano più veicoli effettivi: la selezione automatica è sospesa. "
                         "Controlla l'anagrafica prima di registrare altre spese.")
    if reali:
        return reali[0]
    dimostrativi = [v for v in veicoli if v.get("notes") == NOTA_VEICOLO_TEST]
    if len(dimostrativi) > 1:
        raise ValueError("Risultano più veicoli dimostrativi: controlla l'anagrafica.")
    return dimostrativi[0] if dimostrativi else None


def prepara_auto_unica(client: Client) -> None:
    """Configura il veicolo senza mostrare pulsanti o creare record in lettura."""
    st.session_state.pop("auto_veicolo", None)
    try:
        veicolo = auto_unica(_veicoli(client))
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere i dati dell'auto. Nessun dato modificato.")
        return
    if veicolo is not None:
        st.session_state["auto_veicolo"] = veicolo["id"]


def mostra_auto(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Percorrenza")
    veicolo_id = st.session_state.get("auto_veicolo")
    if not veicolo_id:
        st.info("Nessun chilometro registrato. Inserisci il primo mese nella maschera in alto.")
        return
    try:
        veicolo = next((v for v in _veicoli(client) if v["id"] == veicolo_id), None)
        if veicolo is None:
            st.info("Auto non disponibile. Nessuna modifica effettuata.")
            return
        righe = _chilometri(client, anno["id"], veicolo_id)
    except Exception:
        st.error("Impossibile leggere la percorrenza. Nessun dato modificato.")
        return
    if veicolo.get("notes") == NOTA_VEICOLO_TEST or any(r.get("notes") == NOTA_KM_TEST for r in righe):
        st.warning("DATI DI PROVA: la percorrenza mostrata non rappresenta chilometri realmente effettuati.")
    valori = [Decimal(str(r["distance_km"])) for r in righe]
    totale = sum(valori, Decimal("0"))
    stima = totale / len(valori) * 12 if valori else None
    col1, col2 = st.columns(2)
    col1.metric("Chilometri registrati", _formato_km(totale))
    col2.metric("Stima annuale", _formato_km(stima.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)) if stima is not None else "—")
    st.caption("Proiezione = chilometri dei mesi compilati ÷ numero di mesi compilati × 12. I mesi vuoti non contano.")
    indice = {int(r["month"]): r for r in righe}
    st.dataframe([
        {"Mese": MESI[mese - 1],
         "Chilometri": _formato_km(Decimal(str(indice[mese]["distance_km"]))) if mese in indice else "—",
         "Origine": "TEST" if mese in indice and indice[mese].get("notes") == NOTA_KM_TEST else ("Registrato" if mese in indice else "—")}
        for mese in range(1, 13)
    ], hide_index=True, width="stretch")
    if anno["status"] != "open":
        st.info("Anno chiuso: percorrenza in sola lettura.")
