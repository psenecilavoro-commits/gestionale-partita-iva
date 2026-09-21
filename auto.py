"""Scheda Auto, primo passo: percorrenza mensile e proiezione matematica.

I dati di prova sono contrassegnati; nessun costo o parametro fiscale è
calcolato da questa schermata. Un mese vuoto non equivale a zero.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import MESI

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


def mostra_auto(client: Client, anno: dict) -> None:
    st.subheader("Auto · percorrenza")
    st.caption("Chilometri mensili registrati e proiezione annuale. Carburante, autostrada, rate e limiti sono nelle sezioni seguenti.")
    try:
        veicoli = _veicoli(client)
    except Exception:
        st.error("Impossibile leggere i veicoli. Nessun dato modificato.")
        return

    veicolo_test = next((v for v in veicoli if v.get("notes") == NOTA_VEICOLO_TEST), None)
    if anno["status"] == "open" and veicolo_test is None:
        if st.button("Crea veicolo di prova (senza dati reali)"):
            try:
                # Nessun veicolo reale viene modificato e non si caricano altri dati.
                trovato = next((v for v in _veicoli(client) if v.get("notes") == NOTA_VEICOLO_TEST), None)
                if trovato is None:
                    risposta = client.table("vehicles").insert({"label": NOME_TEST, "notes": NOTA_VEICOLO_TEST}).execute()
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Creazione veicolo non confermata")
            except Exception:
                st.error("Creazione non confermata: controlla l'elenco prima di riprovare.")
            else:
                st.rerun()

    if not veicoli:
        st.info("Nessun veicolo registrato. Per confrontare il foglio crea prima il veicolo di prova.")
        return

    etichette = {v["id"]: v["label"] for v in veicoli}
    selezionato = st.selectbox("Veicolo", list(etichette), format_func=lambda ident: etichette[ident], key="auto_veicolo")
    veicolo = next(v for v in veicoli if v["id"] == selezionato)
    try:
        righe = _chilometri(client, anno["id"], selezionato)
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
        return

    if veicolo.get("notes") == NOTA_VEICOLO_TEST and not righe:
        if st.button("Carica 2.000 km di prova a gennaio"):
            try:
                if _chilometri(client, anno["id"], selezionato):
                    raise ValueError("Sono già presenti chilometri: nessun dato di prova inserito.")
                risposta = client.table("vehicle_monthly").insert({
                    "fiscal_year_id": anno["id"], "vehicle_id": selezionato,
                    "month": 1, "distance_km": "2000.00", "notes": NOTA_KM_TEST,
                }).execute()
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Inserimento non confermato")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Caricamento non confermato: controlla la tabella prima di riprovare.")
            else:
                st.rerun()

    if righe:
        with st.expander("Elimina manualmente un mese"):
            mesi_presenti = {f"{MESI[int(r['month']) - 1]} · {r['distance_km']} km": r["id"] for r in righe}
            scelta = st.selectbox("Mese da eliminare", list(mesi_presenti), key="auto_elimina_mese")
            conferma = st.checkbox("Confermo l'eliminazione definitiva del mese selezionato", key="auto_conferma_mese")
            if st.button("Elimina mese", disabled=not conferma):
                try:
                    risposta = (client.table("vehicle_monthly").delete()
                                .eq("id", mesi_presenti[scelta])
                                .eq("fiscal_year_id", anno["id"])
                                .eq("vehicle_id", selezionato).execute())
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Eliminazione non confermata: controlla la tabella prima di riprovare.")
                else:
                    st.rerun()

    if veicolo.get("notes") == NOTA_VEICOLO_TEST and not righe:
        with st.expander("Elimina il veicolo di prova"):
            conferma = st.checkbox("Confermo di eliminare il veicolo di prova", key="auto_conferma_veicolo")
            if st.button("Elimina veicolo di prova", disabled=not conferma):
                try:
                    if _chilometri(client, anno["id"], selezionato):
                        raise ValueError("Elimina prima i mesi registrati.")
                    risposta = (client.table("vehicles").delete()
                                .eq("id", selezionato).eq("notes", NOTA_VEICOLO_TEST).execute())
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Impossibile eliminare il veicolo di prova: controlla i dati collegati.")
                else:
                    st.rerun()
