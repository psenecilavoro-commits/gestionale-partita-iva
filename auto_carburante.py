"""Carburante di prova condiviso fra Auto e Costi; parametri non fiscali definitivi."""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _veicoli
from fatturato import MESI, euro

CODICE = "carburante"
# Marcatori legacy non modificabili senza migrazione del database.
NOTA_CATEGORIA = "Parametri di confronto dal foglio; verificare prima dell'uso reale."
NOTA_TEST = "DATI DI PROVA - carburante gennaio 2027 dal foglio originale"
CENT = Decimal("0.01")


def _categoria(client: Client, anno_id: str) -> dict | None:
    risposta = (client.table("cost_categories")
                .select("id,name,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,notes")
                .eq("fiscal_year_id", anno_id).eq("code", CODICE).limit(1).execute())
    return risposta.data[0] if risposta.data else None


def _spese(client: Client, anno_id: str, categoria_id: str) -> list[dict]:
    from registri import leggi_tutti
    return leggi_tutti(client, "costs", fiscal_year_id=anno_id, category_id=categoria_id)


def _per_mese(righe: list[dict]) -> dict[int, Decimal]:
    risultati = defaultdict(lambda: Decimal("0"))
    for riga in righe:
        risultati[int(riga["expense_date"][5:7])] += Decimal(str(riga["gross_amount"]))
    return dict(risultati)


def _proiezione(righe: list[dict]) -> tuple[Decimal, Decimal | None]:
    mesi = _per_mese(righe)
    totale = sum(mesi.values(), Decimal("0"))
    return totale, totale / len(mesi) * 12 if mesi else None


def _euro(importo: Decimal) -> str:
    return euro(importo.quantize(CENT, rounding=ROUND_HALF_UP))


def _inserisci_prova(client: Client, anno_id: str, veicolo_id: str) -> None:
    if not any(v["id"] == veicolo_id and v.get("notes") == NOTA_VEICOLO_TEST for v in _veicoli(client)):
        raise ValueError("Seleziona prima il veicolo di prova nella scheda Auto.")
    categoria = _categoria(client, anno_id)
    if categoria is None:
        risposta = client.table("cost_categories").insert({
            "fiscal_year_id": anno_id, "code": CODICE, "name": "Carburante",
            "vat_rate": "0.22", "vat_deductible_rate": "1",
            "cost_deductible_rate": "0.8", "notes": NOTA_CATEGORIA,
        }).execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Creazione categoria non confermata")
        categoria = risposta.data[0]
    elif categoria.get("notes") != NOTA_CATEGORIA:
        raise ValueError("La categoria Carburante è già configurata: non la sovrascrivo.")
    gennaio = [r for r in _spese(client, anno_id, categoria["id"])
               if r["vehicle_id"] == veicolo_id and r["expense_date"].startswith("2027-01-")]
    if gennaio:
        raise ValueError("Esiste già carburante per gennaio: nessun importo sovrascritto.")
    risposta = client.table("costs").insert({
        "fiscal_year_id": anno_id, "category_id": categoria["id"], "vehicle_id": veicolo_id,
        "expense_date": "2027-01-01", "description": "Carburante gennaio: importo di prova, data fittizia",
        "gross_amount": "200.00", "amount_includes_vat": True,
        "vat_rate": "0.22", "vat_deductible_rate": "1", "cost_deductible_rate": "0.8",
        "fiscal_competence_year": 2027, "notes": NOTA_TEST,
    }).execute()
    if len(risposta.data or []) != 1:
        raise RuntimeError("Inserimento non confermato")


def mostra_carburante(client: Client, anno: dict) -> None:
    veicolo_id = st.session_state.get("auto_veicolo")
    if not veicolo_id:
        return
    st.divider()
    st.subheader("Auto · carburante")
    st.caption("Il carburante si registra una sola volta e sarà letto anche nella scheda Costi.")
    try:
        veicolo = next((v for v in _veicoli(client) if v["id"] == veicolo_id), None)
        if veicolo is None:
            st.info("Seleziona un veicolo nella sezione Percorrenza.")
            return
        categoria = _categoria(client, anno["id"])
        righe = _spese(client, anno["id"], categoria["id"]) if categoria else []
    except Exception:
        st.error("Impossibile leggere il carburante. Nessun dato modificato.")
        return
    registrazioni = [r for r in righe if r["vehicle_id"] == veicolo_id]
    totale, proiezione = _proiezione(registrazioni)
    c1, c2 = st.columns(2)
    c1.metric("Carburante registrato · lordo", _euro(totale))
    c2.metric("Stima annua carburante · lordo", _euro(proiezione) if proiezione is not None else "—")
    st.caption("Stima = totale dei mesi compilati ÷ numero di mesi compilati × 12. Più spese nello stesso mese contano come un solo mese.")
    if any(r.get("notes") == NOTA_TEST for r in registrazioni):
        st.warning("CARBURANTE DI PROVA: non è una spesa reale; la data del 1° gennaio è fittizia.")
    valori_mensili = _per_mese(registrazioni)
    st.dataframe([{
        "Mese": MESI[mese - 1], "Spesa carburante lorda": _euro(valori_mensili[mese]) if mese in valori_mensili else "—"
    } for mese in range(1, 13)], hide_index=True, width="stretch")
    if anno["status"] != "open":
        st.info("Anno chiuso: carburante in sola lettura.")
        return
    if veicolo.get("notes") == NOTA_VEICOLO_TEST and not any(r["expense_date"].startswith("2027-01-") for r in registrazioni):
        if st.button("Carica 200 € carburante di prova a gennaio", key="auto_carburante_carica"):
            try:
                _inserisci_prova(client, anno["id"], veicolo_id)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Caricamento non confermato: controlla la tabella prima di riprovare.")
            else:
                st.rerun()
    test = [r for r in registrazioni if r.get("notes") == NOTA_TEST]
    for riga in test:
        with st.expander("Elimina carburante di prova gennaio"):
            conferma = st.checkbox("Confermo l'eliminazione dei 200 € di prova", key=f"carburante_conferma_{riga['id']}")
            if st.button("Elimina carburante di prova", key=f"carburante_elimina_{riga['id']}", disabled=not conferma):
                try:
                    risposta = (client.table("costs").delete().eq("id", riga["id"])
                                .eq("fiscal_year_id", anno["id"])
                                .eq("vehicle_id", veicolo_id).eq("notes", NOTA_TEST).execute())
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Eliminazione non confermata: controlla la tabella prima di riprovare.")
                else:
                    st.rerun()


def mostra_carburante_nei_costi(client: Client, anno: dict) -> None:
    """Vista del medesimo record; nessuna seconda registrazione del costo."""
    try:
        categoria = _categoria(client, anno["id"])
        righe = _spese(client, anno["id"], categoria["id"]) if categoria else []
    except Exception:
        st.error("Impossibile leggere il carburante nella scheda Costi.")
        return
    if not righe:
        return
    st.divider()
    st.markdown("**Carburante · collegato alla scheda Auto**")
    if categoria.get("notes") != NOTA_CATEGORIA or any(
        r.get("notes") != NOTA_TEST or not r["vehicle_id"] or not r["amount_includes_vat"]
        for r in righe
    ):
        st.info("Registrazioni carburante non dimostrative: il riepilogo fiscale richiede una configurazione verificata.")
        return
    per_veicolo = defaultdict(list)
    for riga in righe:
        per_veicolo[riga["vehicle_id"]].append(riga)
    lordo_annuo = sum((_proiezione(v)[1] for v in per_veicolo.values()), Decimal("0"))
    iva = lordo_annuo * Decimal(str(categoria["vat_rate"])) / (Decimal("1") + Decimal(str(categoria["vat_rate"])))
    netto = lordo_annuo - iva * Decimal(str(categoria["vat_deductible_rate"]))
    deducibile = netto * Decimal(str(categoria["cost_deductible_rate"]))
    st.warning("PROIEZIONE DI PROVA: valore non effettivo e percentuali non verificate per il 2027.")
    st.dataframe([{
        "Categoria": "Carburante (proiezione da Auto)",
        "Totale IVA compresa": _euro(lordo_annuo), "IVA scorporata": _euro(iva),
        "Costo netto": _euro(netto), "Costo deducibile": _euro(deducibile),
        "Origine": "TEST · stima annuale",
    }], hide_index=True, width="stretch")
    st.caption("Caso dimostrativo: carburante 2.400,00 €; IVA 432,79 €; netto 1.967,21 €; "
               "quota deducibile 1.573,77 €. Il costo non viene inserito una seconda volta.")
