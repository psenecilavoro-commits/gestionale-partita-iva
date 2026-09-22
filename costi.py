"""Costi annuali dimostrativi separati dalle spese effettivamente sostenute.

Le percentuali numeriche sono scenari di prova non validati per il 2027.
"""
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import euro

CENT = Decimal("0.01")
# Identificatore legacy da preservare per distinguere i record gia' salvati.
NOTA_CATEGORIA_TEST = "Parametri di confronto dal foglio; verificare prima dell'uso reale."

VOCI_TEST = (
    {"code": "commercialista", "name": "Commercialista", "gross": "3000.00",
     "vat_rate": "0.22", "vat_deductible_rate": "1", "cost_deductible_rate": "1",
     "notes": "DATI DI PROVA - costo Commercialista dal foglio originale",
     "confronto": "IVA 540,98 €; costo netto e deducibile 2.459,02 €."},
    {"code": "bollo", "name": "Bollo", "gross": "340.97",
     "vat_rate": "0", "vat_deductible_rate": "0", "cost_deductible_rate": "0.8",
     "notes": "DATI DI PROVA - costo Bollo dal foglio originale",
     "confronto": "IVA 0,00 €; costo netto 340,97 €; quota deducibile 272,78 €."},
    {"code": "assicurazione", "name": "Assicurazione", "gross": "1060.86",
     "vat_rate": "0", "vat_deductible_rate": "0", "cost_deductible_rate": "0.8",
     "notes": "DATI DI PROVA - costo Assicurazione dal foglio originale",
     "confronto": "IVA 0,00 €; costo netto 1.060,86 €; quota deducibile 848,69 €."},
)


def _euro_arrotondato(importo: Decimal) -> str:
    return euro(importo.quantize(CENT, rounding=ROUND_HALF_UP))


def _leggi_categoria(client: Client, anno_id: str, codice: str) -> dict | None:
    risposta = (client.table("cost_categories")
                .select("id,name,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,notes")
                .eq("fiscal_year_id", anno_id).eq("code", codice).limit(1).execute())
    return risposta.data[0] if risposta.data else None


def _leggi_stima(client: Client, anno_id: str, categoria_id: str) -> dict | None:
    risposta = (client.table("annual_cost_estimates")
                .select("id,estimated_gross_amount,amount_includes_vat,notes")
                .eq("fiscal_year_id", anno_id).eq("category_id", categoria_id)
                .limit(1).execute())
    return risposta.data[0] if risposta.data else None


def _crea_prova(client: Client, anno_id: str, voce: dict) -> None:
    categoria = _leggi_categoria(client, anno_id, voce["code"])
    if categoria is None:
        risposta = client.table("cost_categories").insert({
            "fiscal_year_id": anno_id, "code": voce["code"], "name": voce["name"],
            "vat_rate": voce["vat_rate"], "vat_deductible_rate": voce["vat_deductible_rate"],
            "cost_deductible_rate": voce["cost_deductible_rate"],
            "notes": NOTA_CATEGORIA_TEST,
        }).execute()
        if len(risposta.data or []) != 1:
            raise RuntimeError("Creazione categoria non confermata")
        categoria = risposta.data[0]
    elif categoria.get("notes") != NOTA_CATEGORIA_TEST:
        raise ValueError(f"La categoria {voce['name']} è già configurata: non la sovrascrivo.")
    if _leggi_stima(client, anno_id, categoria["id"]) is not None:
        raise ValueError(f"Esiste già un costo {voce['name']}: non lo sovrascrivo.")
    risposta = client.table("annual_cost_estimates").insert({
        "fiscal_year_id": anno_id, "category_id": categoria["id"],
        "estimated_gross_amount": voce["gross"], "amount_includes_vat": True,
        "notes": voce["notes"],
    }).execute()
    if len(risposta.data or []) != 1:
        raise RuntimeError("Creazione stima non confermata")


def _elimina_stima_test(client: Client, anno_id: str, stima: dict, nota: str) -> None:
    if stima.get("notes") != nota:
        raise ValueError("Eliminazione consentita qui soltanto per il dato di prova originale.")
    risposta = (client.table("annual_cost_estimates").delete().eq("id", stima["id"])
                .eq("fiscal_year_id", anno_id).eq("notes", nota).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata")


def _calcola(gross: Decimal, categoria: dict, include_iva: bool) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    aliquota = Decimal(str(categoria["vat_rate"]))
    percentuale_iva = Decimal(str(categoria["vat_deductible_rate"]))
    percentuale_costo = Decimal(str(categoria["cost_deductible_rate"]))
    iva = gross * aliquota / (Decimal("1") + aliquota) if include_iva else Decimal("0")
    iva_detraibile = iva * percentuale_iva
    costo_effettivo = gross - iva_detraibile
    deducibile = costo_effettivo * percentuale_costo
    limite = categoria.get("deductible_limit")
    if limite is not None:
        deducibile = min(deducibile, Decimal(str(limite)))
    return iva, iva_detraibile, costo_effettivo, deducibile


def mostra_costi(client: Client, anno: dict) -> None:
    st.subheader("Costi · scenario dimostrativo")
    st.caption("Importi annuali di prova, non spese effettive. Le aliquote utilizzate "
               "sono ipotesi matematiche e non parametri fiscali verificati.")
    try:
        voci = []
        for voce in VOCI_TEST:
            categoria = _leggi_categoria(client, anno["id"], voce["code"])
            stima = _leggi_stima(client, anno["id"], categoria["id"]) if categoria else None
            voci.append((voce, categoria, stima))
    except Exception:
        st.error("Impossibile leggere i costi: nessun dato modificato.")
        return
    if any(stima and stima.get("notes") == voce["notes"] for voce, _, stima in voci):
        st.warning("DATI DI PROVA PRESENTI: questi costi non rappresentano spese reali.")
    risultati = []
    for voce, categoria, stima in voci:
        if not stima:
            continue
        lordo = Decimal(str(stima["estimated_gross_amount"]))
        iva, iva_detraibile, costo, deducibile = _calcola(
            lordo, categoria, bool(stima["amount_includes_vat"])
        )
        risultati.append({
            "Categoria": categoria["name"], "Totale IVA compresa": _euro_arrotondato(lordo),
            "IVA scorporata": _euro_arrotondato(iva),
            "IVA detraibile": _euro_arrotondato(iva_detraibile),
            "Costo al netto dell'IVA detraibile": _euro_arrotondato(costo),
            "Costo deducibile": _euro_arrotondato(deducibile),
            "Origine": "TEST" if stima.get("notes") == voce["notes"] else "Altro",
        })
    if risultati:
        st.dataframe(risultati, hide_index=True, width="stretch")
    else:
        st.info("Non sono ancora presenti costi annuali di prova.")
    for voce, _categoria, stima in voci:
        if stima and stima.get("notes") == voce["notes"]:
            st.caption(f"Caso dimostrativo · {voce['name']}: {voce['confronto']}")
    if anno["status"] != "open":
        st.info("Anno chiuso: costi in sola lettura.")
        return
    for voce, _categoria, stima in voci:
        if stima is None:
            st.write(f"**{voce['name']}**: nessun importo annuale registrato.")
            if st.button(f"Carica costo di prova {voce['name']}", key=f"costo_carica_{voce['code']}"):
                try:
                    _crea_prova(client, anno["id"], voce)
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("Caricamento non confermato. Aggiorna la pagina e controlla prima di riprovare.")
                else:
                    st.rerun()
        elif stima.get("notes") == voce["notes"]:
            with st.expander(f"Elimina il costo di prova {voce['name']}"):
                conferma = st.checkbox(f"Confermo l'eliminazione del costo di prova {voce['name']}",
                                       key=f"costo_conferma_{voce['code']}")
                if st.button(f"Elimina costo di prova {voce['name']}",
                             key=f"costo_elimina_{voce['code']}", disabled=not conferma):
                    try:
                        _elimina_stima_test(client, anno["id"], stima, voce["notes"])
                    except Exception:
                        st.error("Eliminazione non confermata. Controlla la tabella prima di riprovare.")
                    else:
                        st.rerun()
