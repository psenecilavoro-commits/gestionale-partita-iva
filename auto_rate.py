"""Rate auto: test matematico del foglio, non trattamento fiscale validato.

I 39.900 € di costo veicolo e 25.822,84 € di limite sono SOLO valori
benchmark: non vengono memorizzati come caratteristiche di un veicolo reale.
"""
from decimal import Decimal

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _veicoli
from auto_carburante import _euro, _per_mese, _proiezione
from fatturato import MESI

CODICE = "rate_auto"
NOTA_CATEGORIA = "Parametri di confronto dal foglio; verificare prima dell'uso reale."
NOTA_TEST = "DATI DI PROVA - rata auto gennaio 2027 dal foglio originale"
COSTO_AUTO_TEST = Decimal("39900.00")
LIMITE_TEST = Decimal("25822.84")
IVA_TEST = Decimal("0.22")
DEDUCIBILITA_TEST = Decimal("0.8")


def quota_deducibile_test(lordo_annuo: Decimal) -> Decimal:
    """Ricalca Costi!E2 e F2, senza arrotondamenti intermedi."""
    netto_auto = COSTO_AUTO_TEST / (1 + IVA_TEST)
    rapporto = DEDUCIBILITA_TEST * LIMITE_TEST / netto_auto
    rata_netto = lordo_annuo / (1 + IVA_TEST)
    return rata_netto * rapporto


def _categoria(client: Client, anno_id: str) -> dict | None:
    r = (client.table("cost_categories")
         .select("id,vat_rate,vat_deductible_rate,cost_deductible_rate,notes")
         .eq("fiscal_year_id", anno_id).eq("code", CODICE).limit(1).execute())
    return r.data[0] if r.data else None


def _rate(client: Client, anno_id: str, categoria_id: str) -> list[dict]:
    from registri import leggi_tutti
    return leggi_tutti(client, "costs", fiscal_year_id=anno_id, category_id=categoria_id)


def _carica(client: Client, anno_id: str, veicolo_id: str) -> None:
    if not any(v["id"] == veicolo_id and v.get("notes") == NOTA_VEICOLO_TEST for v in _veicoli(client)):
        raise ValueError("Seleziona il veicolo di prova.")
    categoria = _categoria(client, anno_id)
    if categoria is None:
        r = client.table("cost_categories").insert({
            "fiscal_year_id": anno_id, "code": CODICE, "name": "Rate auto",
            "vat_rate": "0.22", "vat_deductible_rate": "1",
            "cost_deductible_rate": "0.8", "notes": NOTA_CATEGORIA,
        }).execute()
        if len(r.data or []) != 1:
            raise RuntimeError("Categoria non confermata")
        categoria = r.data[0]
    if categoria.get("notes") != NOTA_CATEGORIA:
        raise ValueError("Categoria Rate auto già configurata: nessuna sovrascrittura.")
    if any(r["vehicle_id"] == veicolo_id and r["expense_date"].startswith("2027-01-")
           for r in _rate(client, anno_id, categoria["id"])):
        raise ValueError("Gennaio contiene già rate auto: nessuna sovrascrittura.")
    r = client.table("costs").insert({
        "fiscal_year_id": anno_id, "category_id": categoria["id"],
        "vehicle_id": veicolo_id, "expense_date": "2027-01-01",
        "description": "Rata auto di prova, data fittizia: NON fattura reale",
        "gross_amount": "670.00", "amount_includes_vat": True,
        "vat_rate": "0.22", "vat_deductible_rate": "1",
        "cost_deductible_rate": "0.8", "fiscal_competence_year": 2027,
        "notes": NOTA_TEST,
    }).execute()
    if len(r.data or []) != 1:
        raise RuntimeError("Rata di prova non confermata")


def mostra_rate(client: Client, anno: dict) -> None:
    veicolo_id = st.session_state.get("auto_veicolo")
    if not veicolo_id:
        return
    st.divider()
    st.subheader("Auto · rate auto")
    st.caption("Prima confrontiamo solo le rate lorde. Una rata reale può contenere componenti con trattamenti fiscali diversi.")
    try:
        veicolo = next((v for v in _veicoli(client) if v["id"] == veicolo_id), None)
        if veicolo is None:
            st.info("Seleziona un veicolo.")
            return
        categoria = _categoria(client, anno["id"])
        righe = _rate(client, anno["id"], categoria["id"]) if categoria else []
    except Exception:
        st.error("Impossibile leggere le rate auto. Nessun dato modificato.")
        return
    righe_veicolo = [r for r in righe if r["vehicle_id"] == veicolo_id]
    totale, stima = _proiezione(righe_veicolo)
    c1, c2 = st.columns(2)
    c1.metric("Rate registrate · lordo", _euro(totale))
    c2.metric("Rate stimate nell'anno · lordo", _euro(stima) if stima is not None else "—")
    importi_per_mese = _per_mese(righe_veicolo)
    st.dataframe([
        {"Mese": MESI[m - 1], "Rate lorde": _euro(importi_per_mese[m])
         if m in importi_per_mese else "—"}
        for m in range(1, 13)
    ], hide_index=True, width="stretch")
    if any(r.get("notes") == NOTA_TEST for r in righe_veicolo):
        st.warning("RATE DI PROVA: importi e date non corrispondono a rate reali.")
    if anno["status"] != "open":
        st.info("Anno chiuso: rate in sola lettura.")
        return
    if veicolo.get("notes") == NOTA_VEICOLO_TEST and not any(
        r["expense_date"].startswith("2027-01-") for r in righe_veicolo
    ):
        if st.button("Carica rata auto di prova da 670 € a gennaio", key="rate_carica"):
            try:
                _carica(client, anno["id"], veicolo_id)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Inserimento non confermato: controlla la tabella prima di riprovare.")
            else:
                st.rerun()
    for riga in righe_veicolo:
        if riga.get("notes") != NOTA_TEST:
            continue
        with st.expander("Elimina rata auto di prova gennaio"):
            ok = st.checkbox("Confermo l'eliminazione della rata di prova", key=f"rata_ok_{riga['id']}")
            if st.button("Elimina rata di prova", key=f"rata_elimina_{riga['id']}", disabled=not ok):
                try:
                    r = (client.table("costs").delete().eq("id", riga["id"])
                         .eq("fiscal_year_id", anno["id"])
                         .eq("vehicle_id", veicolo_id).eq("notes", NOTA_TEST).execute())
                    if len(r.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Eliminazione non confermata: controlla la tabella.")
                else:
                    st.rerun()
