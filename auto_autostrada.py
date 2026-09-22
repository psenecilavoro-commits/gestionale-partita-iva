"""Autostrada: singola spesa di prova condivisa con Costi, non duplicata."""
from collections import defaultdict
from decimal import Decimal

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _veicoli
from auto_carburante import _euro, _proiezione, _per_mese
from fatturato import MESI

CODICE = "autostrada"
# Marcatori storici dei record demo da conservare esattamente.
NOTA_CATEGORIA = "Parametri di confronto dal foglio; verificare prima dell'uso reale."
NOTA_TEST = "DATI DI PROVA - autostrada gennaio 2027 dal foglio originale"


def _categoria(client: Client, anno_id: str) -> dict | None:
    risposta = (client.table("cost_categories")
                .select("id,name,vat_rate,vat_deductible_rate,cost_deductible_rate,notes")
                .eq("fiscal_year_id", anno_id).eq("code", CODICE).limit(1).execute())
    return risposta.data[0] if risposta.data else None


def _spese(client: Client, anno_id: str, categoria_id: str) -> list[dict]:
    from registri import leggi_tutti
    return leggi_tutti(client, "costs", fiscal_year_id=anno_id, category_id=categoria_id)


def _inserisci_prova(client: Client, anno_id: str, veicolo_id: str) -> None:
    if not any(v["id"] == veicolo_id and v.get("notes") == NOTA_VEICOLO_TEST for v in _veicoli(client)):
        raise ValueError("Seleziona il veicolo di prova nella scheda Auto.")
    categoria = _categoria(client, anno_id)
    if categoria is None:
        risposta = client.table("cost_categories").insert({
            "fiscal_year_id": anno_id, "code": CODICE, "name": "Autostrada",
            "vat_rate": "0.22", "vat_deductible_rate": "1",
            "cost_deductible_rate": "0.8", "notes": NOTA_CATEGORIA,
        }).execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Creazione categoria non confermata")
        categoria = risposta.data[0]
    if (categoria.get("notes") != NOTA_CATEGORIA
            or Decimal(str(categoria["vat_rate"])) != Decimal("0.22")
            or Decimal(str(categoria["vat_deductible_rate"])) != Decimal("1")
            or Decimal(str(categoria["cost_deductible_rate"])) != Decimal("0.8")):
        raise ValueError("Categoria Autostrada già personalizzata: nessun parametro sovrascritto.")
    if any(r["vehicle_id"] == veicolo_id and r["expense_date"].startswith("2027-01-")
           for r in _spese(client, anno_id, categoria["id"])):
        raise ValueError("Autostrada di gennaio già presente: nessuna spesa sovrascritta.")
    risposta = client.table("costs").insert({
        "fiscal_year_id": anno_id, "category_id": categoria["id"],
        "vehicle_id": veicolo_id, "expense_date": "2027-01-01",
        "description": "Autostrada gennaio: dato di prova, data fittizia",
        "gross_amount": "50.00", "amount_includes_vat": True,
        "vat_rate": "0.22", "vat_deductible_rate": "1",
        "cost_deductible_rate": "0.8", "fiscal_competence_year": 2027,
        "notes": NOTA_TEST,
    }).execute()
    if len(risposta.data or []) != 1:
        raise RuntimeError("Inserimento non confermato")


def mostra_autostrada(client: Client, anno: dict) -> None:
    veicolo_id = st.session_state.get("auto_veicolo")
    if not veicolo_id:
        return
    st.divider()
    st.subheader("Auto · autostrada")
    st.caption("Il costo viene registrato una sola volta, qui, e letto anche nella scheda Costi.")
    try:
        veicolo = next((v for v in _veicoli(client) if v["id"] == veicolo_id), None)
        if veicolo is None:
            st.info("Seleziona un veicolo nella sezione Percorrenza.")
            return
        categoria = _categoria(client, anno["id"])
        righe = _spese(client, anno["id"], categoria["id"]) if categoria else []
    except Exception:
        st.error("Impossibile leggere l'autostrada. Nessun dato modificato.")
        return
    registrazioni = [r for r in righe if r["vehicle_id"] == veicolo_id]
    totale, proiezione = _proiezione(registrazioni)
    c1, c2 = st.columns(2)
    c1.metric("Autostrada registrata · lordo", _euro(totale))
    c2.metric("Stima annua autostrada · lordo", _euro(proiezione) if proiezione is not None else "—")
    st.caption("Stima = totale ÷ mesi compilati × 12; più spese nello stesso mese contano come un solo mese.")
    if any(r.get("notes") == NOTA_TEST for r in registrazioni):
        st.warning("AUTOSTRADA DI PROVA: il costo non è reale e la data del 1° gennaio è fittizia.")
    mensili = _per_mese(registrazioni)
    st.dataframe([{
        "Mese": MESI[mese - 1], "Spesa autostrada lorda": _euro(mensili[mese]) if mese in mensili else "—"
    } for mese in range(1, 13)], hide_index=True, width="stretch")
    if anno["status"] != "open":
        st.info("Anno chiuso: autostrada in sola lettura.")
        return
    if veicolo.get("notes") == NOTA_VEICOLO_TEST and not any(
        r["expense_date"].startswith("2027-01-") for r in registrazioni
    ):
        if st.button("Carica 50 € autostrada di prova a gennaio", key="auto_autostrada_carica"):
            try:
                _inserisci_prova(client, anno["id"], veicolo_id)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Caricamento non confermato: controlla la tabella prima di riprovare.")
            else:
                st.rerun()
    for riga in registrazioni:
        if riga.get("notes") != NOTA_TEST:
            continue
        with st.expander("Elimina autostrada di prova gennaio"):
            conferma = st.checkbox("Confermo l'eliminazione dei 50 € di prova", key=f"autostrada_conferma_{riga['id']}")
            if st.button("Elimina autostrada di prova", key=f"autostrada_elimina_{riga['id']}", disabled=not conferma):
                try:
                    risposta = (client.table("costs").delete()
                                .eq("id", riga["id"]).eq("fiscal_year_id", anno["id"])
                                .eq("vehicle_id", veicolo_id).eq("notes", NOTA_TEST).execute())
                    if len(risposta.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Eliminazione non confermata: controlla la tabella prima di riprovare.")
                else:
                    st.rerun()


def mostra_autostrada_nei_costi(client: Client, anno: dict) -> None:
    """Sola lettura del record Auto; non crea un secondo costo."""
    try:
        categoria = _categoria(client, anno["id"])
        righe = _spese(client, anno["id"], categoria["id"]) if categoria else []
    except Exception:
        st.error("Impossibile leggere l'autostrada nella scheda Costi.")
        return
    if not righe:
        return
    st.divider()
    st.markdown("**Autostrada · collegata alla scheda Auto**")
    if (categoria.get("notes") != NOTA_CATEGORIA
        or any(r.get("notes") != NOTA_TEST or not r["vehicle_id"] or not r["amount_includes_vat"]
               or Decimal(str(r["vat_rate"])) != Decimal("0.22")
               or Decimal(str(r["vat_deductible_rate"])) != Decimal("1")
               or Decimal(str(r["cost_deductible_rate"])) != Decimal("0.8")
               for r in righe)):
        st.info("Presenti spese Autostrada non dimostrative: per il riepilogo fiscale occorre una configurazione verificata.")
        return
    per_veicolo = defaultdict(list)
    for riga in righe:
        per_veicolo[riga["vehicle_id"]].append(riga)
    proiezioni = [_proiezione(v)[1] for v in per_veicolo.values()]
    lordo = sum((val for val in proiezioni if val is not None), Decimal("0"))
    iva = lordo * Decimal("22") / Decimal("122")
    netto = lordo - iva
    deducibile = netto * Decimal("0.8")
    st.warning("PROIEZIONE DI PROVA: non è una spesa effettiva; aliquote da verificare per il 2027.")
    st.dataframe([{
        "Categoria": "Autostrada (proiezione da Auto)", "Totale IVA compresa": _euro(lordo),
        "IVA scorporata": _euro(iva), "Costo netto": _euro(netto),
        "Costo deducibile": _euro(deducibile), "Origine": "TEST · stima annuale",
    }], hide_index=True, width="stretch")
    st.caption("Caso dimostrativo: lordo 600,00 €; IVA 108,20 €; netto 491,80 €; "
               "quota deducibile 393,44 €. Nessuna doppia registrazione.")
