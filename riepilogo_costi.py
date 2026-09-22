"""Riepilogo di sette voci dimostrative, senza mescolare spese reali."""
from collections import defaultdict
from decimal import Decimal

import streamlit as st
from supabase import Client

from auto_rate import CODICE as CODICE_RATE, NOTA_TEST as NOTA_RATE, quota_deducibile_test
from costi import NOTA_CATEGORIA_TEST, _calcola, _euro_arrotondato

# Marcatori storici: mantenere inalterati per riconoscere gli esempi salvati.
ANNUE = {
    "commercialista": "DATI DI PROVA - costo Commercialista dal foglio originale",
    "bollo": "DATI DI PROVA - costo Bollo dal foglio originale",
    "assicurazione": "DATI DI PROVA - costo Assicurazione dal foglio originale",
    "manutenzione_auto": "DATI DI PROVA - manutenzione auto annuale dal foglio originale",
}
MENSILI = {
    "carburante": "DATI DI PROVA - carburante gennaio 2027 dal foglio originale",
    "autostrada": "DATI DI PROVA - autostrada gennaio 2027 dal foglio originale",
    CODICE_RATE: NOTA_RATE,
}
VOCI = {**ANNUE, **MENSILI}


def _somma_mensile_per_veicolo(righe: list[dict]) -> Decimal:
    per_veicolo: dict[str, dict[int, Decimal]] = defaultdict(lambda: defaultdict(lambda: Decimal("0")))
    for r in righe:
        mese = int(str(r["expense_date"])[5:7])
        per_veicolo[r["vehicle_id"]][mese] += Decimal(str(r["gross_amount"]))
    return sum((sum(mesi.values(), Decimal("0")) / len(mesi) * 12
                for mesi in per_veicolo.values()), Decimal("0"))


def calcola_riepilogo(client: Client, anno_id: str) -> tuple[list[dict], list[str], bool]:
    cat = (client.table("cost_categories")
           .select("id,code,name,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,notes")
           .eq("fiscal_year_id", anno_id).execute()).data or []
    categorie = {c["code"]: c for c in cat if c["code"] in VOCI}
    stime = (client.table("annual_cost_estimates")
             .select("category_id,estimated_gross_amount,amount_includes_vat,notes")
             .eq("fiscal_year_id", anno_id).execute()).data or []
    per_categoria = {r["category_id"]: r for r in stime}
    spese = (client.table("costs")
             .select("category_id,vehicle_id,expense_date,gross_amount,amount_includes_vat,notes")
             .eq("fiscal_year_id", anno_id).execute()).data or []
    spese_per_categoria = defaultdict(list)
    for r in spese:
        spese_per_categoria[r["category_id"]].append(r)
    risultati = []
    mancanti = []
    non_test = False
    for codice, nota in VOCI.items():
        categoria = categorie.get(codice)
        if not categoria:
            mancanti.append(codice)
            continue
        if categoria.get("notes") != NOTA_CATEGORIA_TEST:
            non_test = True
            continue
        if codice in ANNUE:
            stima = per_categoria.get(categoria["id"])
            if not stima:
                mancanti.append(codice)
                continue
            if stima.get("notes") != nota or not stima["amount_includes_vat"]:
                non_test = True
                continue
            lordo = Decimal(str(stima["estimated_gross_amount"]))
        else:
            righe = spese_per_categoria[categoria["id"]]
            if not righe:
                mancanti.append(codice)
                continue
            if any(r.get("notes") != nota or not r["amount_includes_vat"] or not r["vehicle_id"]
                   for r in righe):
                non_test = True
                continue
            lordo = _somma_mensile_per_veicolo(righe)
        iva, _iva_detraibile, netto, deducibile = _calcola(lordo, categoria, True)
        if codice == CODICE_RATE:
            if any(Decimal(str(categoria[k])) != v for k, v in (
                ("vat_rate", Decimal("0.22")),
                ("vat_deductible_rate", Decimal("1")),
                ("cost_deductible_rate", Decimal("0.8")),
            )):
                non_test = True
                continue
            deducibile = quota_deducibile_test(lordo)
        risultati.append({"Voce": categoria["name"], "Lordo": lordo,
                          "IVA": iva, "Netto": netto, "Deducibile": deducibile})
    return risultati, mancanti, non_test


def mostra_riepilogo_costi(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Riepilogo spese annuali · scenario")
    st.caption("Quattro stime annuali di prova e tre proiezioni da Auto. Nessuna spesa viene registrata qui.")
    try:
        righe, mancanti, non_test = calcola_riepilogo(client, anno["id"])
    except Exception:
        st.error("Impossibile leggere il riepilogo: nessun dato modificato.")
        return
    if non_test:
        st.warning("Dati ordinari o parametri modificati: scenario sospeso per non mescolare dati reali e di prova.")
        return
    if mancanti:
        st.info("Riepilogo di prova incompleto: carica le voci mancanti: " + ", ".join(mancanti) + ".")
    if not righe:
        return
    st.warning("VALORI DI PROVA: non sono spese effettive né un calcolo fiscale validato per il 2027.")
    st.dataframe([{
        "Voce": r["Voce"], "Lordo annuo": _euro_arrotondato(r["Lordo"]),
        "IVA scorporata": _euro_arrotondato(r["IVA"]),
        "Costo netto": _euro_arrotondato(r["Netto"]),
        "Quota deducibile": _euro_arrotondato(r["Deducibile"]),
    } for r in righe], hide_index=True, width="stretch")
    if mancanti:
        return
    totali = [sum((r[chiave] for r in righe), Decimal("0"))
              for chiave in ("Lordo", "IVA", "Netto", "Deducibile")]
    st.dataframe([{
        "Totale spese di prova": "Totale delle 7 voci",
        "Lordo": _euro_arrotondato(totali[0]),
        "IVA scorporata": _euro_arrotondato(totali[1]),
        "Netto": _euro_arrotondato(totali[2]),
        "Deducibile": _euro_arrotondato(totali[3]),
    }], hide_index=True, width="stretch")
    attesi = (Decimal("15941.83"), Decimal("2621.97"),
              Decimal("13319.86"), Decimal("10047.95"))
    if all(val.quantize(Decimal("0.01")) == atteso for val, atteso in zip(totali, attesi)):
        st.success("I quattro totali del caso dimostrativo coincidono con i valori attesi.")
    else:
        st.warning("Il caso dimostrativo presenta differenze: controlla le singole voci.")
