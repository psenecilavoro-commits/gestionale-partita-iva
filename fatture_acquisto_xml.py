"""Prefill da XML FatturaPA: sola proposta, conferma umana prima della scrittura.

Non conserva bytes, testo integrale o file nel DB. Non ricava da solo
l'IVA detraibile o la data reale di ricezione/registrazione.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from hashlib import sha256

import streamlit as st
from supabase import Client

from fatturato import euro, importo_valido
from iva_acquisti import _inserisci_o_aggiorna, leggi_fatture_iva, valida_fattura

D = Decimal
CENT = D("0.01")
MAX_BYTES = 3 * 1024 * 1024
TIPI_CREDITO = {"TD04", "TD08"}


def _tag(elemento) -> str:
    return elemento.tag.rsplit("}", 1)[-1]


def _figlio(elemento, nome: str):
    return next((x for x in elemento if _tag(x) == nome), None) if elemento is not None else None


def _percorso(elemento, *nomi: str):
    for nome in nomi:
        elemento = _figlio(elemento, nome)
        if elemento is None:
            return None
    return elemento


def _testo(elemento, *nomi: str) -> str:
    trovato = _percorso(elemento, *nomi)
    return (trovato.text or "").strip() if trovato is not None else ""


def _importo_xml(testo: str) -> D:
    try:
        importo = D(testo.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise ValueError("IVA presente nel documento ma non leggibile.") from exc
    if (not importo.is_finite() or importo < 0 or importo > D("999999999999.99")
            or importo != importo.quantize(CENT)):
        raise ValueError("IVA XML non valida o non espressa in centesimi.")
    return importo


def estrai_fattura_xml(dati: bytes) -> dict:
    """Accetta un solo corpo fattura; non confonde IVA con imponibile o pagamento."""
    if not dati or len(dati) > MAX_BYTES:
        raise ValueError("Seleziona un XML fino a 3 MB.")
    from defusedxml import ElementTree as ET
    try:
        radice = ET.fromstring(dati)
    except Exception as exc:
        raise ValueError("XML non leggibile o non sicuro.") from exc
    corpi = [e for e in radice if _tag(e) == "FatturaElettronicaBody"]
    if len(corpi) != 1:
        raise ValueError("XML con zero o più corpi fattura: registra le fatture singolarmente.")
    corpo = corpi[0]
    header = next((e for e in radice if _tag(e) == "FatturaElettronicaHeader"), None)
    generale = _percorso(corpo, "DatiGenerali", "DatiGeneraliDocumento")
    if generale is None:
        raise ValueError("Non trovo i dati generali del documento XML.")
    tipo = _testo(generale, "TipoDocumento")
    if tipo in TIPI_CREDITO:
        raise ValueError("È una nota di credito: occorre gestire le rettifiche, non inserirla come IVA positiva.")
    numero = _testo(generale, "Numero")
    data_t = _testo(generale, "Data")
    if not numero or not data_t:
        raise ValueError("Numero o data fattura mancanti nel documento XML.")
    try:
        data_fattura = date.fromisoformat(data_t)
    except ValueError as exc:
        raise ValueError("Data fattura XML non valida.") from exc
    anagrafica = _percorso(header, "CedentePrestatore", "DatiAnagrafici", "Anagrafica")
    fornitore = _testo(anagrafica, "Denominazione")
    if not fornitore:
        fornitore = " ".join(x for x in (
            _testo(anagrafica, "Nome"), _testo(anagrafica, "Cognome")
        ) if x)
    if not fornitore:
        raise ValueError("Fornitore non identificabile: inserisci la fattura manualmente.")
    riepiloghi = [e for e in corpo.iter() if _tag(e) == "DatiRiepilogo"]
    imposte = []
    for riga in riepiloghi:
        valore = _testo(riga, "Imposta")
        if not valore:
            # IVA non indicata, ad esempio operazione esente: non inventare 0.
            imposte = []
            break
        imposte.append(_importo_xml(valore))
    totale_iva = sum(imposte, D("0")) if imposte else None
    return {
        "supplier": fornitore[:200], "invoice_number": numero[:100],
        "invoice_date": data_fattura, "vat_amount": totale_iva,
        "tipo_documento": tipo or "Non specificato",
        "righe_iva": len(imposte),
    }


def mostra_importa_xml_acquisti(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Importa una fattura d'acquisto XML")
    st.caption("Estrae dal file FatturaPA fornitore, numero, data e IVA esposta. "
               "Data operazione, ricezione, registrazione e detraibilità restano "
               "DA VERIFICARE. Il file non viene archiviato in Supabase.")
    if anno["status"] != "open":
        st.info("Anno chiuso: importazione disattivata.")
        return
    caricato = st.file_uploader("Scegli il file XML della fattura", type=["xml"],
                                key=f"iva_xml_upload_{anno['id']}")
    if caricato is None:
        return
    try:
        dati_file = caricato.getvalue()
        proposta = estrai_fattura_xml(dati_file)
        gia_salvate = leggi_fatture_iva(client, anno["id"])
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("File o registro IVA non leggibile: nessun dato modificato.")
        return
    st.info(f"XML {proposta['tipo_documento']} · fornitore: {proposta['supplier']} · "
            f"n. {proposta['invoice_number']} · data {proposta['invoice_date'].isoformat()} · "
            f"IVA indicata: {euro(proposta['vat_amount']) if proposta['vat_amount'] is not None else 'da inserire'}.")
    impronta = sha256(dati_file).hexdigest()[:16]
    with st.form(f"iva_xml_conferma_{anno['id']}_{impronta}"):
        c1, c2 = st.columns(2)
        fornitore = c1.text_input("Fornitore verificato", value=proposta["supplier"])
        numero = c2.text_input("Numero fattura verificato", value=proposta["invoice_number"])
        fattura = c1.date_input("Data fattura verificata", value=proposta["invoice_date"])
        operazione = c2.date_input("Data operazione (verifica; proposta = data fattura)",
                                  value=proposta["invoice_date"])
        ricezione = c1.date_input("Data effettiva ricezione (modifica se diversa)", value=date.today())
        registrazione = c2.date_input("Data effettiva registrazione (modifica se diversa)", value=date.today())
        categoria = st.radio("Tipo IVA", ["altro", "auto"], horizontal=True,
                             format_func=lambda c: "Altra IVA" if c == "altro" else "IVA auto")
        iva = c1.text_input("IVA complessiva in fattura (€)",
                            value=(str(proposta["vat_amount"]).replace(".", ",")
                                   if proposta["vat_amount"] is not None else ""))
        detraibile = c2.text_input("Quota IVA realmente detraibile verificata (€)",
                                  value="", help="Non è dedotta automaticamente dall'XML; 0 va scritto intenzionalmente.")
        anticipa = st.checkbox("Scelgo l'anticipo al mese dell'operazione, se consentito dalle date")
        nota = st.text_input("Nota facoltativa", max_chars=500)
        confermo = st.checkbox("Ho verificato documento, date reali, importi, detraibilità e anno IVA.")
        salva = st.form_submit_button("Registra fattura XML verificata", type="primary")
    if not salva:
        return
    if not confermo:
        st.warning("Conferma esplicitamente tutti i dati prima della registrazione.")
        return
    try:
        record = valida_fattura({
            "supplier": fornitore, "invoice_number": numero,
            "invoice_date": fattura, "operation_date": operazione,
            "received_date": ricezione, "registered_date": registrazione,
            "vat_amount": importo_valido(iva), "deductible_vat": importo_valido(detraibile),
            "category": categoria, "anticipate": anticipa, "notes": nota,
        }, int(anno["fiscal_year"]))
        attuali = leggi_fatture_iva(client, anno["id"])
        duplicata = any(
            r["supplier"].strip().casefold() == record["supplier"].casefold()
            and r["invoice_number"].strip().casefold() == record["invoice_number"].casefold()
            and r["invoice_date"] == record["invoice_date"]
            for r in attuali
        )
        if duplicata:
            st.warning("Questa fattura risulta già registrata: non è stato aggiunto nulla.")
            return
        _inserisci_o_aggiorna(client, anno["id"], record, None)
    except ValueError as exc:
        st.warning(str(exc))
    except Exception as exc:
        if str(getattr(exc, "code", "")) == "23505":
            st.warning("Fattura già registrata: nessun duplicato aggiunto.")
        else:
            st.error("Salvataggio non confermato: controlla il registro prima di riprovare.")
    else:
        st.success("Fattura registrata dopo la tua verifica.")
        st.rerun()
