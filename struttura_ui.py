"""Completamento funzionale con componenti Streamlit standard, senza styling."""
from datetime import date
from decimal import Decimal as D
import streamlit as st
from registri import leggi_tutti, salva, denaro
from struttura_calcoli import (valida_vendita, valida_periodo, saldo_iva,
                              data_anno, contributi_per_cassa, scenario_cassa)
from fatturato import euro, importo_valido, leggi_fatturato
from quadro_mensile import _csv_bytes


def _carica(client, tabella, anno):
    try:
        campi = "*,version,vat_month" if tabella == "sales_vat_invoices" else "*,version"
        return leggi_tutti(client, tabella, campi, fiscal_year_id=anno["id"])
    except Exception as exc:
        if str(getattr(exc, "code", "")) in ("42P01", "PGRST205", "42703", "PGRST204"):
            st.info("Sezione predisposta: serve SQL_COMPLETAMENTO_STRUTTURA.sql nel solo Supabase Partita IVA. Lo script non è stato applicato da questa attività.")
        else:
            st.error("Registro non accessibile: controlla connessione e permessi. Nessun dato modificato.")
        return None


def _scelta(righe, key, etichetta):
    indice = {r["id"]: r for r in righe}
    scelta = st.selectbox(etichetta, [None, *indice], key=key,
                         format_func=lambda k: "Nuova registrazione" if k is None else
                         " · ".join(str(indice[k].get(c, "")) for c in
                                     ("invoice_number", "description", "payment_date", "month_from", "month_to")
                                     if indice[k].get(c) is not None))
    return indice.get(scelta)


def _operazione(client, tabella, anno, dati, r, elimina, conferma):
    if not conferma:
        raise ValueError("Conferma i dati e l'operazione prima di salvare.")
    salva(client, tabella, anno, dati, r, elimina)


def _errore(exc):
    if isinstance(exc, ValueError):
        st.warning(str(exc))
    elif str(getattr(exc, "code", "")) in ("23505", "23P01"):
        st.warning("Registrazione duplicata o periodo sovrapposto. Ricarica il registro.")
    else:
        st.error("Operazione non confermata: ricarica il registro prima di riprovare.")


def mostra_vendite(client, anno):
    st.subheader("IVA vendite documentata")
    st.caption("Registra imponibile e IVA effettiva del documento, anche con aliquote miste. Il mese IVA è confermato manualmente. Le note di credito riducono solo questo registro; il Fatturato mensile resta distinto e va riconciliato.")
    tabella = "sales_vat_invoices"
    righe = _carica(client, tabella, anno)
    if righe is None:
        return
    from mandanti import elenco_mandanti
    try:
        mandanti = {r["id"]: r for r in elenco_mandanti(client)}
    except Exception:
        st.error("Mandanti non disponibili.")
        return
    if not mandanti:
        st.info("Registra prima una mandante per associare il documento IVA.")
        return
    vista = [{"Mandante": mandanti.get(r["principal_id"], {}).get("name", "Non disponibile"), "Documento": r["invoice_number"],
              "Data": r["invoice_date"], "Tipo": r["document_type"], "Mese IVA": r["vat_month"],
              "Imponibile": r["taxable_amount"], "IVA": r["vat_amount"]} for r in righe]
    st.dataframe(vista, hide_index=True)
    st.download_button("Esporta vendite CSV", _csv_bytes(vista), f"vendite_{anno['fiscal_year']}.csv")
    if anno["status"] != "open":
        st.info("Anno chiuso: sola lettura.")
        return
    r = _scelta(righe, f"vendite_{anno['id']}", "Documento da registrare o modificare")
    base = r or {}
    with st.form(f"vendita_{anno['id']}_{base.get('id', 'new')}_{base.get('version', 0)}"):
        dati = {
            "principal_id": st.selectbox("Mandante documento IVA", list(mandanti), index=list(mandanti).index(base["principal_id"]) if base.get("principal_id") in mandanti else 0, format_func=lambda k: mandanti[k]["name"]),
            "invoice_number": st.text_input("Numero documento", value=base.get("invoice_number", "")),
            "invoice_date": st.date_input("Data documento", value=date.fromisoformat(base["invoice_date"]) if r else date(int(anno["fiscal_year"]), 1, 1)).isoformat(),
            "vat_month": st.number_input("Mese IVA confermato", 1, 12, int(base.get("vat_month") or 1)),
            "document_type": st.selectbox("Tipo documento", ["fattura", "nota_credito"], index=1 if base.get("document_type") == "nota_credito" else 0),
        }
        imponibile = st.text_input("Imponibile documento (€, positivo anche per nota credito)", value=str(base.get("taxable_amount", "")))
        iva = st.text_input("IVA documento (€, positiva anche per nota credito)", value=str(base.get("vat_amount", "")))
        elimina = st.checkbox("Elimina documento selezionato", disabled=r is None)
        conferma = st.checkbox("Confermo documento, importi, periodo e operazione")
        invia = st.form_submit_button("Conferma documento IVA")
    if invia:
        try:
            if not elimina:
                dati.update(taxable_amount=str(importo_valido(imponibile)), vat_amount=str(importo_valido(iva)))
                dati = valida_vendita(dati, int(anno["fiscal_year"]))
            _operazione(client, tabella, anno, dati, r, elimina, conferma)
        except Exception as exc:
            _errore(exc)
        else:
            st.rerun()


def mostra_periodi_iva(client, anno):
    st.subheader("Prospetti IVA per periodo")
    st.warning("Prospetto documentale da verificare, non liquidazione definitiva. Credito iniziale, rettifiche e interessi sono importi confermati manualmente; nessun riporto automatico da bozze. La conferma di completezza non certifica il trattamento fiscale.")
    righe = _carica(client, "vat_periods", anno)
    vendite = _carica(client, "sales_vat_invoices", anno)
    if righe is None or vendite is None:
        return
    from iva_acquisti import leggi_fatture_iva
    try:
        acquisti = leggi_fatture_iva(client, anno["id"])
        vista = []
        for r in righe:
            valori = saldo_iva(vendite, acquisti, r)
            vista.append({"Dal mese": r["month_from"], "Al mese": r["month_to"],
                          "Modalità": r["frequency"], "Documenti completi dichiarati": r["documents_complete"],
                          **{k: euro(v) if v is not None else "Da completare" for k, v in valori.items()},
                          "Versato": r["paid_amount"], "Data versamento": r.get("payment_date")})
    except Exception:
        st.error("Prospetto non disponibile: verificare il registro acquisti e i periodi.")
        return
    st.dataframe(vista, hide_index=True)
    st.download_button("Esporta prospetti IVA CSV", _csv_bytes(vista), f"prospetti_iva_{anno['fiscal_year']}.csv")
    if anno["status"] != "open":
        return
    r = _scelta(righe, f"periodi_{anno['id']}", "Periodo da registrare o modificare")
    b = r or {}
    with st.form(f"periodo_{anno['id']}_{b.get('id', 'new')}_{b.get('version', 0)}"):
        dati = {"frequency": st.selectbox("Periodicità", ["mensile", "trimestrale"], index=1 if b.get("frequency") == "trimestrale" else 0),
                "month_from": st.number_input("Primo mese", 1, 12, int(b.get("month_from", 1))),
                "month_to": st.number_input("Ultimo mese", 1, 12, int(b.get("month_to", 1)))}
        testi = {}
        for campo, label in (("opening_credit", "Credito precedente confermato"), ("adjustment", "Rettifiche (+ debito / − credito)"),
                             ("interest_amount", "Interessi confermati"), ("paid_amount", "Versamento realmente effettuato")):
            testi[campo] = st.text_input(label + " (€; indicare 0 se assente)", value=str(b.get(campo, "")))
        dati["payment_date"] = st.text_input("Data versamento (AAAA-MM-GG; vuota senza versamento)", value=b.get("payment_date") or "").strip() or None
        dati["documents_complete"] = st.checkbox("Ho riconciliato tutti i documenti del periodo, anche se non vi sono fatture", value=bool(b.get("documents_complete")))
        elimina = st.checkbox("Elimina periodo selezionato", disabled=r is None)
        conferma = st.checkbox("Confermo gli importi manuali e l'operazione")
        invia = st.form_submit_button("Conferma periodo IVA")
    if invia:
        try:
            if not elimina:
                for campo, testo in testi.items():
                    segno = -1 if campo == "adjustment" and testo.strip().startswith("-") else 1
                    dati[campo] = str(importo_valido(testo.strip().removeprefix("-")) * segno)
                aggiornati = leggi_tutti(client, "vat_periods", fiscal_year_id=anno["id"])
                valida_periodo(dati, int(anno["fiscal_year"]), [x for x in aggiornati if not r or x["id"] != r["id"]])
            _operazione(client, "vat_periods", anno, dati, r, elimina, conferma)
        except Exception as exc:
            _errore(exc)
        else:
            st.rerun()


def mostra_pensione(client, anno):
    st.subheader("Fondo pensione · versamenti effettivi")
    st.caption("Registro separato dai 5.300 € di prova. Non reinserire pagamenti già presenti nelle deduzioni generiche: riconciliali prima. Il limite deducibile sarà uno scenario esplicito nel conto economico.")
    righe = _carica(client, "pension_payments", anno)
    if righe is None:
        return
    vista = [{"Data": r["payment_date"], "Causale": r["description"], "Importo versato": r["amount"]} for r in righe]
    st.dataframe(vista, hide_index=True)
    st.download_button("Esporta versamenti pensione CSV", _csv_bytes(vista), f"pensione_{anno['fiscal_year']}.csv")
    if anno["status"] != "open":
        return
    r = _scelta(righe, f"pensione_{anno['id']}", "Versamento pensione da registrare o modificare")
    b = r or {}
    with st.form(f"pensione_form_{anno['id']}_{b.get('id', 'new')}_{b.get('version', 0)}"):
        descrizione = st.text_input("Causale versamento pensione", value=b.get("description", ""))
        pagamento = st.date_input("Data versamento pensione", value=date.fromisoformat(b["payment_date"]) if r else date(int(anno["fiscal_year"]), 1, 1))
        importo = st.text_input("Importo versato pensione (€)", value=str(b.get("amount", "")))
        elimina = st.checkbox("Elimina versamento pensione selezionato", disabled=r is None)
        conferma = st.checkbox("Confermo pagamento documentato, assenza di doppioni e operazione")
        invia = st.form_submit_button("Conferma versamento pensione")
    if invia:
        try:
            dati = {}
            if not elimina:
                data_anno(pagamento, int(anno["fiscal_year"]))
                valore = importo_valido(importo)
                if not descrizione.strip() or len(descrizione.strip()) > 200 or valore <= 0:
                    raise ValueError("Causale obbligatoria (massimo 200 caratteri) e importo positivo.")
                dati = {"description": descrizione.strip(), "payment_date": pagamento.isoformat(), "amount": str(valore)}
            _operazione(client, "pension_payments", anno, dati, r, elimina, conferma)
        except Exception as exc:
            _errore(exc)
        else:
            st.rerun()


def mostra_conto_registrato(client, anno):
    st.subheader("Conto economico · registrazioni e scenario a cassa")
    st.warning("Variante distinta dalle formule letterali del foglio: usa contributi effettivamente versati nell'anno e fondo pensione documentato. Aliquote, limiti e ammissibilità restano scenari da verificare; nessun netto disponibile o debito definitivo.")
    try:
        ricavi = leggi_fatturato(client, anno["id"])
        costi = leggi_tutti(client, "costs", fiscal_year_id=anno["id"])
        deduzioni = leggi_tutti(client, "tax_deductions", fiscal_year_id=anno["id"])
        pensione = _carica(client, "pension_payments", anno)
        if pensione is None:
            return
        if any(str(r.get("notes") or "").startswith("DATI DI PROVA") for r in ricavi + costi):
            st.info("Scenario sulle registrazioni sospeso: sono presenti dati di prova in Fatturato o Costi.")
            return
        contributi = contributi_per_cassa(deduzioni, int(anno["fiscal_year"]))
        fatturato = sum((denaro(r["amount"]) for r in ricavi), D(0))
        spese = sum((denaro(r["gross_amount"]) for r in costi), D(0))
        for r in pensione:
            data_anno(r["payment_date"], int(anno["fiscal_year"]))
        versato_pensione = sum((denaro(r["amount"]) for r in pensione), D(0))
        from imposte_parametri import _leggi
        p = {k: D(str(v["value"])) for k, v in _leggi(client, anno["id"]).items()}
    except Exception:
        st.error("Registrazioni incomplete o incoerenti: scenario non calcolato.")
        return
    st.dataframe([{"Voce": k, "Importo registrato": euro(v)} for k, v in {
        "Fatturato integrale": fatturato, "Costi registrati (importi come inseriti)": spese,
        "INPS versato": contributi["INPS"], "Di cui INPS competenza precedente": contributi["INPS_AP"],
        "Enasarco documentato": contributi["ENASARCO"], "Pensione versata": versato_pensione}.items()], hide_index=True)
    st.caption("Le stime annuali dei costi sono escluse. Le deduzioni generiche e le detrazioni non sono applicate automaticamente: la spettanza sarà controllata nella fase successiva. L'importo deducibile dei costi è confermato qui per evitare di trattare aliquote di prova come regole fiscali.")
    costi_testo = st.text_input("Costi deducibili confermati per lo scenario (€)", key=f"cassa_costi_{anno['id']}")
    limite_testo = st.text_input("Limite pensione ipotizzato per l'anno (€; non verificato)", key=f"cassa_limite_{anno['id']}")
    conferma = st.checkbox("Ho riconciliato ricavi, costi e versamenti dell'anno; gli eventuali registri vuoti significano zero", key=f"cassa_completezza_{anno['id']}")
    if not conferma or not costi_testo.strip() or not limite_testo.strip():
        return
    try:
        valori = scenario_cassa(fatturato, importo_valido(costi_testo), contributi,
                               versato_pensione, importo_valido(limite_testo), p)
    except KeyError:
        st.info("Completa i parametri IRPEF di scenario nella scheda Imposte.")
        return
    except ValueError as exc:
        st.warning(str(exc))
        return
    vista = [{"Voce scenario": k, "Importo": euro(v)} for k, v in valori.items()]
    st.dataframe(vista, hide_index=True)
    st.download_button("Esporta scenario a cassa CSV", _csv_bytes(vista), f"scenario_cassa_{anno['fiscal_year']}.csv")


def mostra_riconciliazione(client, anno):
    st.subheader("Riconciliazione fatture acquisto e costi")
    st.caption("Collegamento uno a uno: non genera spese e non somma nuovamente gli importi IVA. Documenti ripartiti su più costi restano da verificare manualmente.")
    links = _carica(client, "purchase_cost_links", anno)
    if links is None:
        return
    try:
        from iva_acquisti import leggi_fatture_iva
        fatture = {r["id"]: r for r in leggi_fatture_iva(client, anno["id"])}
        costi = {r["id"]: r for r in leggi_tutti(client, "costs", fiscal_year_id=anno["id"])}
        vista = [{"Fattura": fatture[r["purchase_id"]]["invoice_number"],
                  "Fornitore": fatture[r["purchase_id"]]["supplier"],
                  "Costo": costi[r["cost_id"]]["description"]} for r in links]
    except Exception:
        st.error("Riconciliazione non disponibile: verificare i registri e i collegamenti.")
        return
    st.dataframe(vista, hide_index=True)
    st.caption(f"Fatture senza collegamento: {len(fatture) - len(links)} · Costi senza collegamento: {len(costi) - len(links)}. Non tutti i costi richiedono una fattura IVA.")
    if anno["status"] != "open":
        return
    if links:
        scelto = st.selectbox("Collegamento da rimuovere", [r["id"] for r in links],
                             format_func=lambda k: next(fatture[r["purchase_id"]]["invoice_number"] for r in links if r["id"] == k), key=f"link_remove_{anno['id']}")
        if st.button("Rimuovi solo il collegamento", key=f"link_delete_{anno['id']}"):
            try:
                salva(client, "purchase_cost_links", anno, {}, next(r for r in links if r["id"] == scelto), True)
            except Exception as exc:
                _errore(exc)
            else:
                st.rerun()
    disponibili_f = [k for k in fatture if k not in {r["purchase_id"] for r in links}]
    disponibili_c = [k for k in costi if k not in {r["cost_id"] for r in links}]
    if not disponibili_f or not disponibili_c:
        return
    with st.form(f"link_new_{anno['id']}"):
        f = st.selectbox("Fattura da collegare", disponibili_f, format_func=lambda k: f"{fatture[k]['supplier']} · {fatture[k]['invoice_number']}")
        c = st.selectbox("Costo già registrato", disponibili_c, format_func=lambda k: f"{costi[k]['description']} · {costi[k]['gross_amount']}")
        ok = st.checkbox("Ho verificato che fattura e costo rappresentino la stessa spesa")
        invia = st.form_submit_button("Collega senza duplicare il costo")
    if invia:
        try:
            _operazione(client, "purchase_cost_links", anno, {"purchase_id": f, "cost_id": c}, None, False, ok)
        except Exception as exc:
            _errore(exc)
        else:
            st.rerun()
