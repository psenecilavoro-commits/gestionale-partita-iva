"""Inserimento manuale delle tre spese auto nella sola scheda Auto.

Legge/scrive la stessa tabella costs usata nel riepilogo generale: nessuna
seconda registrazione né modifica delle percentuali fiscali preesistenti.
Le spese dimostrative conservano i loro comandi dedicati e non sono editabili qui.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _veicoli
from costi_tabella import CONFIG, _crea_categoria
from fatturato import euro, importo_valido
from registri import anno_aperto, leggi_tutti
from struttura_calcoli import data_anno

AUTO_CODICI = ("carburante", "autostrada", "rate_auto")
NOTA_REALE = "Spesa auto inserita manualmente; parametri fiscali da verificare"


def valida_spesa_auto(codice: str, giorno: date, importo: Decimal,
                       anno: int, *, oggi: date | None = None) -> None:
    if codice not in AUTO_CODICI:
        raise ValueError("Questa spesa non appartiene alle tre categorie auto gestite qui.")
    data_anno(giorno, anno, oggi=oggi)
    if not importo.is_finite() or importo <= 0:
        raise ValueError("Inserisci un importo positivo e valido.")


def mostra_spese_auto(client: Client, anno: dict) -> None:
    """Editor unico dei tre tipi: storico e aggregati restano nelle viste esistenti."""
    st.divider()
    st.subheader("Auto · registra e modifica le spese")
    st.caption("Carburante, autostrada e rate si inseriscono soltanto qui. "
               "Il registrato e la proiezione annuale compaiono anche nel riepilogo Costi. "
               "La registrazione non equivale a una fattura IVA o a un pagamento verificato.")
    selezionato = st.session_state.get("auto_veicolo")
    if not selezionato:
        st.info("Seleziona prima un veicolo nella sezione Percorrenza.")
        return
    try:
        veicolo = next((v for v in _veicoli(client) if v["id"] == selezionato), None)
        if veicolo is None:
            st.info("Il veicolo non è più disponibile: selezionalo nuovamente.")
            return
        categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])
        indice = {c["code"]: c for c in categorie if c["code"] in AUTO_CODICI}
        spese = leggi_tutti(client, "costs", fiscal_year_id=anno["id"], vehicle_id=selezionato)
        id_categorie = {c["id"]: c["code"] for c in indice.values()}
        righe = [r for r in spese if r["category_id"] in id_categorie]
    except Exception:
        st.error("Impossibile leggere le spese auto. Nessun dato modificato.")
        return
    manuali = [r for r in righe if not str(r.get("notes") or "").startswith("DATI DI PROVA")]
    if manuali:
        st.dataframe([{
            "Tipo": CONFIG[id_categorie[r["category_id"]]][1],
            "Data": r["expense_date"],
            "Descrizione": r["description"],
            "Importo lordo": euro(Decimal(str(r["gross_amount"]))),
        } for r in manuali], hide_index=True, width="stretch")
    if anno["status"] != "open":
        st.info("Anno chiuso: le spese sono in sola lettura.")
        return
    if veicolo.get("notes") == NOTA_VEICOLO_TEST:
        st.info("Per inserire una spesa effettiva, seleziona o crea un veicolo non dimostrativo. "
                "Le spese di prova si gestiscono nei rispettivi riquadri precedenti.")
        return

    codice = st.selectbox("Tipo di spesa auto", AUTO_CODICI,
                          format_func=lambda k: CONFIG[k][1],
                          key=f"auto_spesa_tipo_{anno['id']}")
    categoria = indice.get(codice)
    esistenti = [r for r in manuali if categoria and r["category_id"] == categoria["id"]]
    per_id = {r["id"]: r for r in esistenti}
    scelta = st.selectbox("Spesa da aggiungere o modificare", [None, *per_id],
                         format_func=lambda ident: (
                             "Nuova spesa" if ident is None else
                             f"{per_id[ident]['expense_date']} · {per_id[ident]['description']} "
                             f"({euro(Decimal(str(per_id[ident]['gross_amount'])))})"),
                         key=f"auto_spesa_scelta_{anno['id']}_{codice}")
    precedente = per_id.get(scelta)
    anno_num = int(anno["fiscal_year"])
    # L'anno selezionato può essere futuro: il widget deve ricevere una data
    # compresa nei suoi limiti, anche se l'inserimento sarà bloccato fino ad allora.
    giorno_predefinito = max(date(anno_num, 1, 1),
                             min(date.today(), date(anno_num, 12, 31)))
    with st.form(f"auto_spesa_form_{anno['id']}_{codice}_{scelta or 'nuova'}"):
        giorno = st.date_input("Data della spesa", value=(
            date.fromisoformat(precedente["expense_date"]) if precedente
            else giorno_predefinito),
            min_value=date(anno_num, 1, 1),
            max_value=date(anno_num, 12, 31))
        descrizione = st.text_input("Descrizione", value=(
            precedente["description"] if precedente else CONFIG[codice][1]),
            max_chars=200)
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
            if precedente is None:
                raise ValueError("Seleziona la spesa da eliminare.")
            richiesta = (client.table("costs").delete().eq("id", precedente["id"])
                        .eq("fiscal_year_id", anno["id"])
                        .eq("category_id", categoria["id"])
                        .eq("vehicle_id", selezionato)
                        .eq("gross_amount", precedente["gross_amount"])
                        .eq("expense_date", precedente["expense_date"]))
        else:
            valore = importo_valido(testo)
            valida_spesa_auto(codice, giorno, valore, anno_num)
            descrizione = " ".join(descrizione.split())
            if not descrizione or len(descrizione) > 200:
                raise ValueError("Inserisci una descrizione di massimo 200 caratteri.")
            if categoria is None:
                categoria = _crea_categoria(client, anno["id"], codice)
            dati = {
                "expense_date": giorno.isoformat(), "description": descrizione,
                "gross_amount": str(valore), "amount_includes_vat": include_iva,
            }
            if precedente is not None:
                # Mantieni aliquote, competenza e note già presenti sul record.
                richiesta = (client.table("costs").update(dati)
                            .eq("id", precedente["id"])
                            .eq("fiscal_year_id", anno["id"])
                            .eq("category_id", categoria["id"])
                            .eq("vehicle_id", selezionato)
                            .eq("gross_amount", precedente["gross_amount"])
                            .eq("expense_date", precedente["expense_date"]))
            else:
                dati.update({
                    "fiscal_year_id": anno["id"], "category_id": categoria["id"],
                    "vehicle_id": selezionato,
                    "vat_rate": categoria["vat_rate"],
                    "vat_deductible_rate": categoria["vat_deductible_rate"],
                    "cost_deductible_rate": categoria["cost_deductible_rate"],
                    "fiscal_competence_year": anno_num,
                    "notes": NOTA_REALE,
                })
                richiesta = client.table("costs").insert(dati)
        risposta = richiesta.execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Scrittura non confermata o record modificato da un'altra sessione.")
    except ValueError as exc:
        st.warning(str(exc))
    except Exception:
        st.error("Operazione non confermata. Verifica i dati prima di riprovare.")
    else:
        st.rerun()
