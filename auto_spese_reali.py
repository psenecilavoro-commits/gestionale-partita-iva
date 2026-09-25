"""Maschera unica Auto: percorrenza, carburante, autostrada e rate.

Usa i registri esistenti e associa automaticamente le registrazioni all'unica
auto effettiva. L'auto è creata solo al primo salvataggio confermato, non in
lettura. I dati dimostrativi restano separati e non sono modificabili qui.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _chilometri, _km_validi, _veicoli
from costi_tabella import CONFIG, _crea_categoria
from fatturato import MESI, euro, importo_valido
from registri import anno_aperto, leggi_tutti
from struttura_calcoli import data_anno

AUTO_CODICI = ("carburante", "autostrada", "rate_auto")
NOTA_REALE = "Spesa auto inserita manualmente; parametri fiscali da verificare"
NOTA_KM_REALE = "Percorrenza effettiva dichiarata"
TIPI = ("percorrenza", *AUTO_CODICI)
ETICHETTE = {"percorrenza": "Percorrenza", "carburante": "Carburante",
             "autostrada": "Autostrada", "rate_auto": "Rate auto"}


def valida_spesa_auto(codice: str, giorno: date, importo: Decimal,
                       anno: int, *, oggi: date | None = None) -> None:
    if codice not in AUTO_CODICI:
        raise ValueError("Questa spesa non appartiene alle tre categorie auto gestite qui.")
    data_anno(giorno, anno, oggi=oggi)
    if not importo.is_finite() or importo <= 0:
        raise ValueError("Inserisci un importo positivo e valido.")


def _auto_effettiva(client: Client) -> str:
    """Riuso dell'unico veicolo reale; creazione solo durante un salvataggio esplicito."""
    veicoli = _veicoli(client)
    reali = [v for v in veicoli if v.get("notes") != NOTA_VEICOLO_TEST]
    if len(reali) > 1:
        raise ValueError("Sono presenti più veicoli effettivi: impossibile associare automaticamente la registrazione.")
    if reali:
        return reali[0]["id"]
    risposta = client.table("vehicles").insert({
        "label": "Auto", "notes": "Registrazione manuale",
    }).execute()
    if len(risposta.data or []) != 1 or not risposta.data[0].get("id"):
        raise RuntimeError("Auto non creata: nessuna registrazione confermata.")
    return risposta.data[0]["id"]


def _maschera_percorrenza(client: Client, anno: dict, veicolo_id: str | None) -> None:
    anno_num = int(anno["fiscal_year"])
    try:
        righe = _chilometri(client, anno["id"], veicolo_id) if veicolo_id else []
    except Exception:
        st.error("Impossibile leggere i chilometri. Nessuna modifica effettuata.")
        return
    # Nessuna sovrascrittura accidentale dei chilometri dimostrativi.
    manuali = [r for r in righe if not str(r.get("notes") or "").startswith("DATI DI PROVA")]
    per_mese = {int(r["month"]): r for r in manuali}
    if len(per_mese) != len(manuali):
        st.error("Sono presenti mesi duplicati: controlla i dati prima di modificarli.")
        return
    scelta = st.selectbox("Operazione sulla percorrenza", [None, *sorted(per_mese)],
                         format_func=lambda m: "Nuovo mese" if m is None else f"Modifica {MESI[m - 1]}",
                         key=f"auto_km_scelta_{anno['id']}")
    precedente = per_mese.get(scelta)
    with st.form(f"auto_km_form_{anno['id']}_{scelta or 'nuovo'}"):
        if precedente is None:
            mese = st.selectbox("Mese", list(range(1, 13)),
                                format_func=lambda m: MESI[m - 1],
                                key=f"auto_km_mese_{anno['id']}")
        else:
            mese = int(precedente["month"])
            st.write(f"Mese: **{MESI[mese - 1]}**")
        testo = st.text_input("Chilometri effettivi (0 se il mese è realmente a zero)",
                              value=str(precedente["distance_km"]).replace(".", ",") if precedente else "",
                              placeholder="es. 1800,50")
        elimina = st.checkbox("Elimina il mese selezionato", disabled=precedente is None)
        conferma = st.checkbox("Confermo la percorrenza e l'eventuale eliminazione")
        invia = st.form_submit_button("Salva percorrenza", type="primary")
    if not invia:
        return
    try:
        anno_aperto(client, anno)
        if not conferma:
            raise ValueError("Conferma prima l'operazione sulla percorrenza.")
        if elimina:
            if precedente is None or not veicolo_id:
                raise ValueError("Seleziona un mese esistente da eliminare.")
            richiesta = (client.table("vehicle_monthly").delete()
                        .eq("id", precedente["id"]).eq("fiscal_year_id", anno["id"])
                        .eq("vehicle_id", veicolo_id).eq("month", mese)
                        .eq("distance_km", precedente["distance_km"]))
        else:
            valore = _km_validi(testo)
            if date(anno_num, mese, 1) > date.today():
                raise ValueError("Non registrare come effettiva una percorrenza futura.")
            if precedente is None and any(int(r["month"]) == mese for r in righe):
                raise ValueError("Questo mese è già registrato: usa Modifica o controlla i dati di prova.")
            vid = _auto_effettiva(client)
            if precedente is not None:
                richiesta = (client.table("vehicle_monthly").update({
                                "distance_km": str(valore), "notes": NOTA_KM_REALE,
                            }).eq("id", precedente["id"]).eq("fiscal_year_id", anno["id"])
                            .eq("vehicle_id", vid).eq("month", mese)
                            .eq("distance_km", precedente["distance_km"]))
            else:
                if _chilometri(client, anno["id"], vid) and any(
                        int(r["month"]) == mese for r in _chilometri(client, anno["id"], vid)):
                    raise ValueError("Il mese è già presente: nessun dato sovrascritto.")
                richiesta = client.table("vehicle_monthly").insert({
                    "fiscal_year_id": anno["id"], "vehicle_id": vid,
                    "month": mese, "distance_km": str(valore), "notes": NOTA_KM_REALE,
                })
        risposta = richiesta.execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Salvataggio non confermato o mese cambiato da un'altra sessione.")
    except ValueError as exc:
        st.warning(str(exc))
    except Exception:
        st.error("Operazione non confermata: controlla la percorrenza prima di riprovare.")
    else:
        st.rerun()


def _maschera_spesa(client: Client, anno: dict, veicolo_id: str | None, codice: str) -> None:
    anno_num = int(anno["fiscal_year"])
    try:
        categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])
        categoria = next((c for c in categorie if c["code"] == codice), None)
        spese = leggi_tutti(client, "costs", fiscal_year_id=anno["id"], vehicle_id=veicolo_id) if veicolo_id else []
        manuali = [r for r in spese if categoria and r["category_id"] == categoria["id"]
                   and not str(r.get("notes") or "").startswith("DATI DI PROVA")]
    except Exception:
        st.error("Impossibile leggere le spese auto. Nessun dato modificato.")
        return
    per_id = {r["id"]: r for r in manuali}
    scelta = st.selectbox("Spesa da aggiungere o modificare", [None, *per_id],
                         format_func=lambda ident: (
                             "Nuova spesa" if ident is None else
                             f"{per_id[ident]['expense_date']} · {per_id[ident]['description']} "
                             f"({euro(Decimal(str(per_id[ident]['gross_amount'])))})"),
                         key=f"auto_spesa_scelta_{anno['id']}_{codice}")
    precedente = per_id.get(scelta)
    giorno_predefinito = max(date(anno_num, 1, 1),
                             min(date.today(), date(anno_num, 12, 31)))
    with st.form(f"auto_spesa_form_{anno['id']}_{codice}_{scelta or 'nuova'}"):
        giorno = st.date_input("Data della spesa", value=(
            date.fromisoformat(precedente["expense_date"]) if precedente else giorno_predefinito),
            min_value=date(anno_num, 1, 1), max_value=date(anno_num, 12, 31))
        descrizione = st.text_input("Descrizione", value=(
            precedente["description"] if precedente else ETICHETTE[codice]), max_chars=200)
        testo = st.text_input("Importo lordo (€)", value=(
            str(precedente["gross_amount"]).replace(".", ",") if precedente else ""),
            placeholder="es. 75,00")
        include_iva = st.checkbox("Importo comprensivo di IVA, se prevista",
                                 value=bool(precedente["amount_includes_vat"]) if precedente else True)
        elimina = st.checkbox("Elimina la spesa selezionata", disabled=precedente is None)
        conferma = st.checkbox("Confermo spesa, importi e assenza di registrazioni duplicate")
        invia = st.form_submit_button("Conferma operazione", type="primary")
    if not invia:
        return
    try:
        anno_aperto(client, anno)
        if not conferma:
            raise ValueError("Conferma la registrazione e l'eventuale eliminazione.")
        if elimina:
            if precedente is None or not veicolo_id or categoria is None:
                raise ValueError("Seleziona una spesa esistente da eliminare.")
            richiesta = (client.table("costs").delete().eq("id", precedente["id"])
                        .eq("fiscal_year_id", anno["id"]).eq("category_id", categoria["id"])
                        .eq("vehicle_id", veicolo_id).eq("gross_amount", precedente["gross_amount"])
                        .eq("expense_date", precedente["expense_date"]))
        else:
            valore = importo_valido(testo)
            valida_spesa_auto(codice, giorno, valore, anno_num)
            descrizione = " ".join(descrizione.split())
            if not descrizione or len(descrizione) > 200:
                raise ValueError("Inserisci una descrizione di massimo 200 caratteri.")
            vid = _auto_effettiva(client)
            if categoria is None:
                categoria = _crea_categoria(client, anno["id"], codice)
            dati = {"expense_date": giorno.isoformat(), "description": descrizione,
                    "gross_amount": str(valore), "amount_includes_vat": include_iva}
            if precedente is not None:
                richiesta = (client.table("costs").update(dati).eq("id", precedente["id"])
                            .eq("fiscal_year_id", anno["id"]).eq("category_id", categoria["id"])
                            .eq("vehicle_id", vid).eq("gross_amount", precedente["gross_amount"])
                            .eq("expense_date", precedente["expense_date"]))
            else:
                dati.update({
                    "fiscal_year_id": anno["id"], "category_id": categoria["id"],
                    "vehicle_id": vid, "vat_rate": categoria["vat_rate"],
                    "vat_deductible_rate": categoria["vat_deductible_rate"],
                    "cost_deductible_rate": categoria["cost_deductible_rate"],
                    "fiscal_competence_year": anno_num, "notes": NOTA_REALE,
                })
                richiesta = client.table("costs").insert(dati)
        risposta = richiesta.execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Scrittura non confermata o record cambiato da un'altra sessione.")
    except ValueError as exc:
        st.warning(str(exc))
    except Exception:
        st.error("Operazione non confermata. Verifica i dati prima di riprovare.")
    else:
        st.rerun()


def mostra_spese_auto(client: Client, anno: dict) -> None:
    """Una sola maschera, visualizzata prima di tutti i riepiloghi Auto."""
    st.subheader("Registra o modifica le spese")
    st.caption("Inserisci qui i chilometri mensili oppure una singola spesa di carburante, "
               "autostrada o rata auto. I riepiloghi sottostanti e la scheda Costi "
               "leggono gli stessi record, senza duplicazioni.")
    veicolo_id = st.session_state.get("auto_veicolo")
    try:
        veicolo = next((v for v in _veicoli(client) if v["id"] == veicolo_id), None)
        reali = [v for v in _veicoli(client) if v.get("notes") != NOTA_VEICOLO_TEST]
    except Exception:
        st.error("Impossibile leggere i dati dell'auto. Nessun dato modificato.")
        return
    if len(reali) > 1:
        st.error("Sono presenti più veicoli effettivi: controlla l'anagrafica prima di inserire dati.")
        return
    if veicolo is not None and veicolo.get("notes") == NOTA_VEICOLO_TEST:
        st.info("I dati di prova rimangono separati. La prima registrazione effettiva "
                "sarà associata automaticamente alla tua auto, senza compilare un'anagrafica.")
    elif veicolo is None:
        st.caption("La tua auto sarà associata automaticamente al primo salvataggio, "
                   "senza una registrazione separata del veicolo.")
    if anno["status"] != "open":
        st.info("Anno chiuso: registrazioni in sola lettura.")
        return
    if date(int(anno["fiscal_year"]), 1, 1) > date.today():
        st.info("L'anno selezionato non è ancora iniziato: le spese effettive "
                "e la percorrenza potranno essere registrate dalla data di inizio dell'anno.")
    # Le registrazioni di prova non si modificano mai nell'editor effettivo.
    reale_id = veicolo["id"] if veicolo and veicolo.get("notes") != NOTA_VEICOLO_TEST else None
    tipo = st.selectbox("Che cosa vuoi registrare o modificare?", TIPI,
                        format_func=lambda k: ETICHETTE[k],
                        key=f"auto_tipo_{anno['id']}")
    if tipo == "percorrenza":
        _maschera_percorrenza(client, anno, reale_id)
    else:
        _maschera_spesa(client, anno, reale_id, tipo)
    if int(anno["fiscal_year"]) == 2026:
        st.caption(
            "Le spese auto 2026 sono registrate per il controllo economico del regime "
            "forfettario e non per calcolare una deduzione analitica dal reddito."
        )
    else:
        st.caption("Le spese effettive non equivalgono a fatture IVA documentate. "
                   "I parametri fiscali per il 2027 restano da verificare.")
