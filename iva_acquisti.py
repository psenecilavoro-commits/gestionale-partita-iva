"""Registro IVA acquisti documentati, separato da costi e stime.

Il periodo è indicativo per la sola liquidazione mensile ordinaria. Nessun
file o immagine viene salvato; il commercialista deve confermare la
spettanza della detrazione e i casi particolari.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import streamlit as st
from supabase import Client

from fatturato import MESI, euro, importo_valido
from iva_anteprima import periodo_detrazione

TABELLA = "purchase_vat_invoices"
D = Decimal
CENT = D("0.01")
CAMPI = (
    "id", "supplier", "invoice_number", "invoice_date", "operation_date",
    "received_date", "registered_date", "vat_amount", "deductible_vat",
    "category", "anticipate", "notes",
)


def leggi_fatture_iva(client: Client, anno_id: str) -> list[dict]:
    risultato = (client.table(TABELLA).select(",".join(CAMPI))
                 .eq("fiscal_year_id", anno_id)
                 .order("registered_date").execute())
    return risultato.data or []


def _data(valore: str | date) -> date:
    return valore if isinstance(valore, date) else date.fromisoformat(str(valore))


def periodo_fattura(riga: dict) -> tuple[int, int]:
    """Applica l'anticipo solo se scelto e consentito dalle tre date."""
    operazione = _data(riga["operation_date"])
    ricezione = _data(riga["received_date"])
    registrazione = _data(riga["registered_date"])
    anno_possibile, mese_possibile, anticipabile = periodo_detrazione(
        operazione, ricezione, registrazione
    )
    if riga.get("anticipate"):
        if anticipabile or (anno_possibile, mese_possibile) == (registrazione.year, registrazione.month):
            return anno_possibile, mese_possibile
        raise ValueError("L'anticipo non è applicabile alle date indicate.")
    return registrazione.year, registrazione.month


def valida_fattura(dati: dict, anno: int) -> dict:
    """Valida il record intero prima di qualsiasi scrittura."""
    puliti = dict(dati)
    for campo, limite in (("supplier", 200), ("invoice_number", 100)):
        valore = str(puliti.get(campo) or "").strip()
        if not valore or len(valore) > limite:
            raise ValueError("Fornitore e numero fattura sono obbligatori e devono essere brevi.")
        puliti[campo] = valore
    puliti["notes"] = str(puliti.get("notes") or "").strip()[:500] or None
    for campo in ("invoice_date", "operation_date", "received_date", "registered_date"):
        puliti[campo] = _data(puliti[campo]).isoformat()
    if _data(puliti["invoice_date"]) > _data(puliti["received_date"]):
        raise ValueError("La data della fattura non può essere successiva alla ricezione.")
    if _data(puliti["registered_date"]) > date.today():
        raise ValueError("Una fattura non può essere registrata come già ricevuta in una data futura.")
    iva = D(str(puliti["vat_amount"]))
    detraibile = D(str(puliti["deductible_vat"]))
    if (not iva.is_finite() or not detraibile.is_finite()
            or min(iva, detraibile) < 0 or detraibile > iva
            or iva > D("999999999999.99")
            or iva != iva.quantize(CENT) or detraibile != detraibile.quantize(CENT)):
        raise ValueError("IVA totale e detraibile non valide: 0 ≤ detraibile ≤ IVA fattura.")
    puliti["vat_amount"] = str(iva)
    puliti["deductible_vat"] = str(detraibile)
    if puliti.get("category") not in ("auto", "altro"):
        raise ValueError("Categoria IVA non valida.")
    puliti["anticipate"] = bool(puliti.get("anticipate", False))
    anno_iva, mese_iva = periodo_fattura(puliti)
    if anno_iva != anno:
        raise ValueError(
            f"Questa fattura appartiene all'IVA di {MESI[mese_iva - 1]} {anno_iva}: "
            f"seleziona l'anno {anno_iva} prima di registrarla."
        )
    return puliti


def riepilogo_acquisti_iva(righe: list[dict], anno: int) -> dict[int, dict]:
    """Raggruppa solo registrazioni confermate, distinguendo auto e altre."""
    risultato: dict[int, dict] = {}
    for r in righe:
        anno_iva, mese = periodo_fattura(r)
        if anno_iva != anno:
            raise ValueError("Una fattura appartiene a un altro anno IVA.")
        gruppo = risultato.setdefault(mese, {"auto": D("0"), "altro": D("0"), "count": 0})
        importo = D(str(r["deductible_vat"]))
        totale = D(str(r["vat_amount"]))
        if (not importo.is_finite() or not totale.is_finite() or importo < 0
                or totale < importo or r["category"] not in ("auto", "altro")):
            raise ValueError("Importi IVA registrati incoerenti.")
        gruppo[r["category"]] += importo
        gruppo["count"] += 1
    return risultato


def _indisponibile(exc: Exception) -> bool:
    codice = str(getattr(exc, "code", ""))
    messaggio = str(exc).lower()
    return codice in ("42P01", "PGRST205") or (
        "purchase_vat_invoices" in messaggio
        and ("schema cache" in messaggio or "does not exist" in messaggio)
    )


def _inserisci_o_aggiorna(client: Client, anno_id: str, dati: dict, presente: dict | None) -> None:
    if presente is None:
        risposta = client.table(TABELLA).insert({"fiscal_year_id": anno_id, **dati}).execute()
    else:
        risposta = (client.table(TABELLA).update(dati)
                    .eq("id", presente["id"])
                    .eq("fiscal_year_id", anno_id).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Salvataggio non confermato")


def mostra_registro_iva_acquisti(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Registro IVA fatture d'acquisto")
    st.caption("Importi IVA tratti da fatture effettive e verificati da te: non importa "
               "automaticamente i Costi e non salva file. Non è una liquidazione ufficiale.")
    anno_num = int(anno["fiscal_year"])
    try:
        righe = leggi_fatture_iva(client, anno["id"])
        gruppi = riepilogo_acquisti_iva(righe, anno_num)
    except Exception as exc:
        if _indisponibile(exc):
            st.warning("Per salvare le fatture d'acquisto, esegui SQL_IVA_ACQUISTI.sql "
                       "nel SQL Editor del SOLO Supabase Gestionale Partita IVA, poi aggiorna con F5.")
            st.link_button("Apri lo script SQL", "https://github.com/psenecilavoro-commits/gestionale-partita-iva/blob/main/SQL_IVA_ACQUISTI.sql")
        else:
            st.error("Registro acquisti non accessibile o dati incoerenti. Nessun dato modificato.")
        return

    st.dataframe([{
        "Mese IVA": MESI[m - 1],
        "IVA detraibile auto": euro(gruppi[m]["auto"]) if m in gruppi else "—",
        "Altra IVA detraibile": euro(gruppi[m]["altro"]) if m in gruppi else "—",
        "Totale IVA detraibile registrata": euro(gruppi[m]["auto"] + gruppi[m]["altro"]) if m in gruppi else "—",
        "Fatture": gruppi[m]["count"] if m in gruppi else "—",
    } for m in range(1, 13)], hide_index=True, use_container_width=True)
    if righe:
        with st.expander(f"Mostra le {len(righe)} fatture registrate"):
            st.dataframe([{
                "Fornitore": r["supplier"], "N. fattura": r["invoice_number"],
                "Data fattura": r["invoice_date"], "Operazione": r["operation_date"],
                "Ricezione": r["received_date"], "Registrazione": r["registered_date"],
                "Mese IVA": MESI[periodo_fattura(r)[1] - 1],
                "IVA fattura": euro(D(str(r["vat_amount"]))),
                "IVA detraibile verificata": euro(D(str(r["deductible_vat"]))),
                "Categoria": "Auto" if r["category"] == "auto" else "Altra",
            } for r in righe], hide_index=True, use_container_width=True)
    st.info("Le somme sono soltanto l'IVA detraibile da TE confermata sui documenti presenti. "
            "Non comprendono fatture assenti, IVA a credito precedente, rettifiche o versamenti. "
            "Consulta il commercialista sulla detraibilità effettiva.")
    if anno["status"] != "open":
        st.info("Anno chiuso: registro fatture in sola lettura.")
        return

    opzioni = {r["id"]: r for r in righe}
    opzione = st.selectbox("Registra o modifica una fattura", ["Nuova fattura", *opzioni],
                          format_func=lambda ident: (ident if ident == "Nuova fattura" else
                          f"{opzioni[ident]['supplier']} · {opzioni[ident]['invoice_number']} · "
                          f"{opzioni[ident]['invoice_date']}"),
                          key=f"iva_acquisti_scelta_{anno['id']}")
    presente = opzioni.get(opzione)
    def _data_form(campo: str) -> date:
        return _data(presente[campo]) if presente else date(anno_num, 1, 1)
    def _testo(campo: str) -> str:
        return str(presente.get(campo) or "") if presente else ""

    with st.form(f"iva_acquisti_form_{anno['id']}_{opzione}"):
        c1, c2 = st.columns(2)
        fornitore = c1.text_input("Fornitore / denominazione", value=_testo("supplier"))
        numero = c2.text_input("Numero fattura", value=_testo("invoice_number"))
        data_fattura = c1.date_input("Data fattura", value=_data_form("invoice_date"))
        data_operazione = c2.date_input("Data operazione", value=_data_form("operation_date"))
        data_ricezione = c1.date_input("Data di ricezione", value=_data_form("received_date"))
        data_registrazione = c2.date_input("Data registrazione", value=_data_form("registered_date"))
        categoria = st.radio("Tipo IVA", ("auto", "altro"),
                             format_func=lambda v: "IVA auto" if v == "auto" else "Altra IVA",
                             index=0 if presente and presente["category"] == "auto" else 1,
                             horizontal=True)
        totale_iva = c1.text_input("IVA indicata in fattura (€)",
                                  value=str(presente["vat_amount"]).replace(".", ",") if presente else "")
        detraibile = c2.text_input("IVA effettivamente detraibile verificata (€)",
                                  value=str(presente["deductible_vat"]).replace(".", ",") if presente else "",
                                  help="Inserisci soltanto la quota di IVA che hai verificato come detraibile; può essere 0.")
        anticipa = st.checkbox("Esercito la detrazione nel mese dell'operazione (solo se ricevuta e annotata entro il 15 del mese seguente, stesso anno)",
                               value=bool(presente["anticipate"]) if presente else False)
        nota = st.text_input("Nota facoltativa", value=_testo("notes"), max_chars=500)
        conferma = st.checkbox("Confermo di aver verificato la fattura, le tre date e la quota di IVA detraibile.")
        invia = st.form_submit_button("Salva fattura verificata", type="primary")
    if invia:
        if not conferma:
            st.warning("Conferma la verifica del documento prima di salvare.")
        else:
            try:
                dati = valida_fattura({
                    "supplier": fornitore, "invoice_number": numero,
                    "invoice_date": data_fattura, "operation_date": data_operazione,
                    "received_date": data_ricezione, "registered_date": data_registrazione,
                    "vat_amount": importo_valido(totale_iva),
                    "deductible_vat": importo_valido(detraibile),
                    "category": categoria, "anticipate": anticipa, "notes": nota,
                }, anno_num)
                aggiornate = leggi_fatture_iva(client, anno["id"])
                if presente is not None and next((r for r in aggiornate if r["id"] == presente["id"]), None) != presente:
                    raise ValueError("La fattura è cambiata: aggiorna la pagina e verifica nuovamente.")
                _inserisci_o_aggiorna(client, anno["id"], dati, presente)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                if str(getattr(exc, "code", "")) == "23505":
                    st.warning("Fattura già presente per fornitore, numero e data: nessun duplicato creato.")
                else:
                    st.error("Salvataggio non confermato: controlla il registro prima di riprovare.")
            else:
                st.rerun()

    if presente is not None:
        elimina_ok = st.checkbox("Confermo l'eliminazione definitiva di questa fattura IVA",
                                key=f"iva_acquisti_elimina_ok_{presente['id']}")
        if st.button("Elimina fattura IVA", disabled=not elimina_ok,
                     key=f"iva_acquisti_elimina_btn_{presente['id']}"):
            try:
                risposta = (client.table(TABELLA).delete()
                            .eq("id", presente["id"])
                            .eq("fiscal_year_id", anno["id"]).execute())
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Eliminazione non confermata")
            except Exception:
                st.error("Eliminazione non confermata: controlla il registro.")
            else:
                st.rerun()
