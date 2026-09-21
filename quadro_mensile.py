"""Quadro di controllo della struttura: sola lettura, nessuna liquidazione fiscale.

Importi assenti restano assenti; il 22% sulle vendite e' SOLO la formula del
foglio di riferimento. I CSV si generano in memoria e non vengono archiviati.
"""
from __future__ import annotations

import csv
from decimal import Decimal
from io import StringIO

import streamlit as st
from supabase import Client

from accantonamenti import leggi_accantonamenti
from accantonamenti_completi import leggi_provvigioni_nette
from fatturato import MESI, NOTA_TEST, euro, leggi_fatturato
from iva_acquisti import leggi_fatture_iva, riepilogo_acquisti_iva
from iva_anteprima import iva_vendite_foglio

D = Decimal


def _per_mese_unico(righe: list[dict], campo: str) -> dict[int, D]:
    risultato: dict[int, D] = {}
    for riga in righe:
        mese = int(riga["month"])
        valore = D(str(riga[campo]))
        if (not 1 <= mese <= 12 or mese in risultato or not valore.is_finite()
                or valore < 0):
            raise ValueError("Valore mensile assente, duplicato o non valido")
        risultato[mese] = valore
    return risultato


def _fatturato_mensile(righe: list[dict]) -> dict[int, D]:
    risultato: dict[int, D] = {}
    for riga in righe:
        mese = int(riga["month"])
        valore = D(str(riga["amount"]))
        if not 1 <= mese <= 12 or not valore.is_finite() or valore < 0:
            raise ValueError("Fatturato non valido")
        risultato[mese] = risultato.get(mese, D("0")) + valore
    return risultato


def costruisci_quadro(fatturati: list[dict], nette: list[dict],
                      accantonamenti: list[dict], fatture: list[dict],
                      anno: int) -> tuple[list[dict], list[dict]]:
    """Tabella e verifiche: non promuovere importi parziali a IVA dovuta."""
    ricavi = _fatturato_mensile(fatturati)
    provvigioni = _per_mese_unico(nette, "amount")
    riserve = _per_mese_unico(accantonamenti, "reserved_amount")
    acquisti = riepilogo_acquisti_iva(fatture, anno)
    iva_vendite = iva_vendite_foglio(fatturati)
    prova = {int(r["month"]) for r in fatturati if r.get("notes") == NOTA_TEST}
    righe = []
    controlli = []
    for mese, nome in enumerate(MESI, 1):
        # Almeno una fattura presente NON certifica che tutte siano state caricate.
        documenti = acquisti.get(mese)
        netta = provvigioni.get(mese)
        riserva = riserve.get(mese)
        iva_fatturata = iva_vendite.get(mese)
        iva_acquisti = ((documenti["auto"] + documenti["altro"])
                       if documenti is not None else None)
        differenza_iva = ((iva_fatturata - iva_acquisti)
                         if iva_fatturata is not None and iva_acquisti is not None else None)
        simulazione_netto = ((netta - riserva - differenza_iva)
                            if netta is not None and riserva is not None
                            and differenza_iva is not None else None)
        mancanti = [etichetta for presente, etichetta in (
            (mese in ricavi, "fatturato"),
            (netta is not None, "provvigioni nette"),
            (riserva is not None, "accantonato"),
            (documenti is not None, "fatture acquisto"),
        ) if not presente]
        stato = "Dati di prova" if mese in prova else (
            "Da completare" if mancanti else "Confronto compilabile, non validato"
        )
        righe.append({
            "Mese": nome,
            "Fatturato senza IVA": euro(ricavi[mese]) if mese in ricavi else "—",
            "Provvigioni nette": euro(netta) if netta is not None else "—",
            "Accantonato": euro(riserva) if riserva is not None else "—",
            "IVA vendite · 22% foglio (SIMULAZIONE)": euro(iva_fatturata) if iva_fatturata is not None else "—",
            "IVA acquisti registrata (PARZIALE)": euro(iva_acquisti) if iva_acquisti is not None else "—",
            "Differenza IVA · ipotesi (NON dovuta)": euro(differenza_iva) if differenza_iva is not None else "—",
            "Netto foglio · ipotesi (NON disponibile)": euro(simulazione_netto) if simulazione_netto is not None else "—",
            "Stato": stato,
        })
        controlli.append({
            "Mese": nome,
            "Dati da inserire": ", ".join(mancanti) if mancanti else "Nessun campo mancante tra i quattro monitorati",
            "Fatture IVA acquisti registrate": documenti["count"] if documenti is not None else 0,
            "Avvertenza": "Fatturato di prova" if mese in prova else "Verificare completezza documenti e IVA vendite",
        })
    return righe, controlli


def _sicuro_csv(valore: object) -> str:
    """Protegge le celle testuali da formule in Excel e Google Fogli."""
    testo = "" if valore is None else str(valore)
    if testo.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + testo
    return testo


def _csv_bytes(righe: list[dict]) -> bytes:
    if not righe:
        return b""
    buffer = StringIO(newline="")
    scrittore = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_ALL)
    colonne = list(righe[0])
    scrittore.writerow(colonne)
    for riga in righe:
        scrittore.writerow([_sicuro_csv(riga.get(colonna)) for colonna in colonne])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def mostra_quadro_mensile(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Quadro mensile e controllo dei dati")
    st.caption("Unisce le schede senza duplicare o modificare registrazioni. "
               "Le colonne IVA e netto del foglio sono SOLO simulazioni matematiche, "
               "non liquidazioni né disponibilità finanziaria.")
    try:
        fatturati = leggi_fatturato(client, anno["id"])
        nette = leggi_provvigioni_nette(client, anno["id"])
        riserve = leggi_accantonamenti(client, anno["id"])
        acquisti = leggi_fatture_iva(client, anno["id"])
        tabella, controlli = costruisci_quadro(
            fatturati, nette, riserve, acquisti, int(anno["fiscal_year"])
        )
    except Exception:
        st.warning("Quadro integrato non disponibile: controlla che siano presenti e "
                   "accessibili entrambe le tabelle SQL delle provvigioni nette e "
                   "delle fatture IVA acquisti. Nessun dato modificato.")
        return
    if any(r.get("notes") == NOTA_TEST for r in fatturati):
        st.warning("Attenzione: il fatturato contiene dati di PROVA; non usare i risultati per versamenti.")
    st.dataframe(tabella, hide_index=True, width="stretch")
    st.caption("La presenza di documenti per un mese non ne attesta la completezza; "
               "un campo vuoto NON equivale a zero. Il saldo IVA effettivo richiede "
               "le fatture emesse, i crediti riportati, rettifiche e verifica del commercialista.")
    with st.expander("Controlli mese per mese", expanded=False):
        st.dataframe(controlli, hide_index=True, width="stretch")
    st.markdown("#### Esporta le registrazioni per controllo")
    c1, c2, c3 = st.columns(3)
    c1.download_button("Scarica quadro mensile CSV", _csv_bytes(tabella),
                       file_name=f"quadro_mensile_{anno['fiscal_year']}.csv",
                       mime="text/csv", key=f"csv_quadro_{anno['id']}")
    c2.download_button("Scarica controlli CSV", _csv_bytes(controlli),
                       file_name=f"controlli_dati_{anno['fiscal_year']}.csv",
                       mime="text/csv", key=f"csv_controlli_{anno['id']}")
    fatture_csv = [{
        "Fornitore": r["supplier"], "Numero fattura": r["invoice_number"],
        "Data fattura": r["invoice_date"], "Operazione": r["operation_date"],
        "Ricezione": r["received_date"], "Registrazione": r["registered_date"],
        "IVA fattura": r["vat_amount"], "IVA detraibile verificata": r["deductible_vat"],
        "Categoria": r["category"], "Anticipo scelto": r["anticipate"],
        "Note": r.get("notes") or "",
    } for r in acquisti]
    c3.download_button("Scarica registro acquisti CSV", _csv_bytes(fatture_csv),
                       file_name=f"fatture_iva_acquisti_{anno['fiscal_year']}.csv",
                       mime="text/csv", disabled=not fatture_csv,
                       key=f"csv_iva_acquisti_{anno['id']}")
    st.caption("Esportazioni generate in memoria: nessun documento o file CSV viene salvato nel database.")
