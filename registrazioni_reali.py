"""Anagrafiche e registrazioni ordinarie sulle tabelle già presenti."""
from datetime import date
import streamlit as st
from fatturato import MESI, importo_valido
from registri import leggi_tutti, anno_aperto
from struttura_calcoli import data_anno
from struttura_ui_helpers import errore_scrittura


def _etichetta_veicolo(record):
    if record.get("notes") == "VEICOLO DI PROVA - foglio originale":
        return "Veicolo di prova"
    return record["label"]


def _origine(record):
    """Normalizza solo i marcatori tecnici dimostrativi, senza modificare i dati."""
    nota = str(record.get("notes") or "")
    if nota.startswith("DATI DI PROVA") or nota.startswith("VEICOLO DI PROVA"):
        return "Dati di prova"
    return nota


def mostra_veicoli_reali(client, anno):
    if anno["status"] != "open":
        return
    with st.expander("Registra un veicolo e la percorrenza effettiva"):
        try:
            veicoli = leggi_tutti(client, "vehicles")
        except Exception:
            st.error("Anagrafica veicoli non disponibile.")
            return
        with st.form(f"veicolo_reale_{anno['id']}"):
            nome = st.text_input("Nome o targa del veicolo")
            invia = st.form_submit_button("Aggiungi veicolo reale")
        if invia:
            try:
                anno_aperto(client, anno)
                nome = " ".join(nome.split())
                if not nome or len(nome) > 100:
                    raise ValueError("Nome obbligatorio, massimo 100 caratteri.")
                if any(v["label"].strip().casefold() == nome.casefold() for v in leggi_tutti(client, "vehicles")):
                    raise ValueError("Veicolo già presente.")
                risposta = client.table("vehicles").insert({"label": nome, "notes": "Registrazione manuale"}).execute()
                if len(risposta.data or []) != 1:
                    raise ValueError("Inserimento non confermato: ricarica prima di riprovare.")
            except Exception as exc:
                errore_scrittura(exc)
            else:
                st.rerun()
        if not veicoli:
            return
        ids = {r["id"]: r for r in veicoli}
        vid = st.selectbox("Veicolo per la percorrenza", list(ids),
                           format_func=lambda k: _etichetta_veicolo(ids[k]),
                           key=f"km_veicolo_{anno['id']}")
        mese = st.selectbox("Mese percorrenza", list(range(1, 13)),
                            format_func=lambda m: MESI[m-1], key=f"km_mese_{anno['id']}")
        try:
            esistenti = leggi_tutti(client, "vehicle_monthly", fiscal_year_id=anno["id"], vehicle_id=vid, month=mese)
            if len(esistenti) > 1:
                raise ValueError("Mese duplicato: correggere prima i dati.")
        except Exception:
            st.error("Percorrenza non leggibile o duplicata.")
            return
        r = esistenti[0] if esistenti else None
        with st.form(f"km_reali_{anno['id']}_{vid}_{mese}"):
            km = st.text_input("Chilometri effettivi (0 è un mese compilato)", value=str(r["distance_km"]) if r else "")
            conferma = st.checkbox("Confermo la percorrenza effettiva e l'eventuale sostituzione del mese")
            invia = st.form_submit_button("Salva percorrenza")
        if invia:
            try:
                anno_aperto(client, anno)
                if not conferma:
                    raise ValueError("Conferma prima il dato effettivo.")
                if date(int(anno["fiscal_year"]), mese, 1) > date.today():
                    raise ValueError("Non registrare come effettiva una percorrenza futura.")
                from auto import _km_validi
                dati = {"distance_km": str(_km_validi(km)), "notes": "Percorrenza effettiva dichiarata"}
                if r:
                    risposta = (client.table("vehicle_monthly").update(dati).eq("id", r["id"])
                                .eq("fiscal_year_id", anno["id"]).eq("distance_km", r["distance_km"]).execute())
                else:
                    risposta = client.table("vehicle_monthly").insert({**dati, "fiscal_year_id": anno["id"], "vehicle_id": vid, "month": mese}).execute()
                if len(risposta.data or []) != 1:
                    raise ValueError("Salvataggio non confermato o mese modificato altrove.")
            except Exception as exc:
                errore_scrittura(exc)
            else:
                st.rerun()


def mostra_costi_reali(client, anno):
    st.subheader("Registro delle spese effettive · tutte le categorie")
    if int(anno["fiscal_year"]) == 2026:
        st.caption(
            "Le spese documentate sono distinte dalle stime annuali. Nel modello forfettario "
            "2026 servono al controllo economico e di cassa, ma non riducono analiticamente "
            "il reddito determinato con il coefficiente di redditività."
        )
    else:
        st.caption("Le spese documentate sono distinte dalle stime annuali e non le sostituiscono. L'IVA acquisti va registrata e riconciliata nel registro dedicato. Percentuali fiscali da verificare.")
    try:
        costi = leggi_tutti(client, "costs", fiscal_year_id=anno["id"])
        categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])
    except Exception:
        st.error("Registro costi non disponibile.")
        return
    st.dataframe([{
        "Data": r["expense_date"], "Descrizione": r["description"],
        "Importo": r["gross_amount"], "IVA compresa": r["amount_includes_vat"],
    } for r in costi], hide_index=True)
    from quadro_mensile import _csv_bytes
    st.download_button("Esporta spese registrate CSV",
                       _csv_bytes([{**r, "notes": _origine(r)} for r in costi]),
                       f"spese_{anno['fiscal_year']}.csv")
    if anno["status"] != "open":
        return
    categorie = [r for r in categorie if r["code"] not in ("rate_auto", "carburante", "autostrada", "penale_km")]
    from costi_tabella import CONFIG, _crea_categoria
    mancanti = [k for k, v in CONFIG.items() if v[2] == "annuale" and k not in {r["code"] for r in categorie}]
    if mancanti:
        with st.expander("Prepara una categoria senza inserire stime o spese"):
            codice = st.selectbox("Categoria da preparare", mancanti,
                                  format_func=lambda k: CONFIG[k][1], key=f"categoria_reale_{anno['id']}")
            if st.button("Crea solo la categoria", key=f"categoria_create_{anno['id']}"):
                try:
                    anno_aperto(client, anno)
                    _crea_categoria(client, anno["id"], codice)
                except Exception as exc:
                    errore_scrittura(exc)
                else:
                    st.rerun()
    if not categorie:
        st.info("Prepara una categoria per registrare la prima spesa.")
        return
    cats = {r["id"]: r for r in categorie}
    rows = {r["id"]: r for r in costi if r["category_id"] in cats}
    scelta = st.selectbox("Spesa effettiva da registrare o modificare", [None, *rows],
                         format_func=lambda k: "Nuova spesa" if k is None else f"{rows[k]['expense_date']} · {rows[k]['description']}",
                         key=f"spesa_reale_{anno['id']}")
    r = rows.get(scelta)
    with st.form(f"spesa_form_{anno['id']}_{scelta}"):
        cid = st.selectbox("Categoria spesa", list(cats),
                           index=list(cats).index(r["category_id"]) if r else 0,
                           format_func=lambda k: cats[k]["name"])
        descrizione = st.text_input("Descrizione spesa", value=r["description"] if r else "")
        giorno = st.date_input("Data spesa effettiva", value=date.fromisoformat(r["expense_date"]) if r else date(int(anno["fiscal_year"]), 1, 1))
        importo = st.text_input("Importo della spesa (€)", value=str(r["gross_amount"]) if r else "")
        include = st.checkbox("L'importo comprende IVA", value=bool(r["amount_includes_vat"]) if r else True)
        elimina = st.checkbox("Elimina questa spesa", disabled=r is None)
        conferma = st.checkbox("Confermo documento, assenza di duplicati e operazione sulla spesa")
        invia = st.form_submit_button("Conferma spesa effettiva")
    if invia:
        try:
            anno_aperto(client, anno)
            if not conferma:
                raise ValueError("Conferma prima l'operazione.")
            if elimina:
                risposta = client.table("costs").delete().eq("id", r["id"]).eq("fiscal_year_id", anno["id"]).execute()
            else:
                data_anno(giorno, int(anno["fiscal_year"]))
                if not descrizione.strip() or len(descrizione) > 200:
                    raise ValueError("Descrizione obbligatoria, massimo 200 caratteri.")
                dati = {
                    "category_id": cid, "expense_date": giorno.isoformat(),
                    "description": descrizione.strip(),
                    "gross_amount": str(importo_valido(importo)),
                    "amount_includes_vat": include,
                    "fiscal_competence_year": int(anno["fiscal_year"]),
                    "notes": (r.get("notes") if r and str(r.get("notes") or "").startswith("DATI DI PROVA")
                              else "Spesa effettiva dichiarata; percentuali da verificare"),
                }
                fonte = r if r and cid == r["category_id"] else cats[cid]
                dati.update({k: fonte[k] for k in ("vat_rate", "vat_deductible_rate", "cost_deductible_rate")})
                if r:
                    risposta = (client.table("costs").update(dati).eq("id", r["id"])
                                .eq("fiscal_year_id", anno["id"]).eq("gross_amount", r["gross_amount"]).execute())
                else:
                    risposta = client.table("costs").insert({**dati, "fiscal_year_id": anno["id"]}).execute()
            if len(risposta.data or []) != 1:
                raise ValueError("Operazione non confermata: ricarica i dati.")
        except Exception as exc:
            errore_scrittura(exc)
        else:
            st.rerun()
