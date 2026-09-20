"""Manutenzione auto: stima annuale di PROVA dal foglio, non fattura reale."""
from decimal import Decimal

import streamlit as st
from supabase import Client

from costi import _calcola, _euro_arrotondato, NOTA_CATEGORIA_TEST

CODICE = "manutenzione_auto"
NOTA_TEST = "DATI DI PROVA - manutenzione auto annuale dal foglio originale"


def _categoria(client: Client, anno_id: str) -> dict | None:
    r = (client.table("cost_categories")
         .select("id,name,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,notes")
         .eq("fiscal_year_id", anno_id).eq("code", CODICE).limit(1).execute())
    return r.data[0] if r.data else None


def _stima(client: Client, anno_id: str, categoria_id: str) -> dict | None:
    r = (client.table("annual_cost_estimates")
         .select("id,estimated_gross_amount,amount_includes_vat,notes")
         .eq("fiscal_year_id", anno_id).eq("category_id", categoria_id).limit(1).execute())
    return r.data[0] if r.data else None


def _carica(client: Client, anno_id: str) -> None:
    categoria = _categoria(client, anno_id)
    if categoria is None:
        r = client.table("cost_categories").insert({
            "fiscal_year_id": anno_id, "code": CODICE, "name": "Manutenzione auto",
            "vat_rate": "0.22", "vat_deductible_rate": "1",
            "cost_deductible_rate": "0.8", "notes": NOTA_CATEGORIA_TEST,
        }).execute()
        if len(r.data or []) != 1:
            raise RuntimeError("Categoria non confermata")
        categoria = r.data[0]
    if categoria.get("notes") != NOTA_CATEGORIA_TEST:
        raise ValueError("Categoria già configurata: nessuna sovrascrittura.")
    if _stima(client, anno_id, categoria["id"]) is not None:
        raise ValueError("Manutenzione già presente: nessuna sovrascrittura.")
    r = client.table("annual_cost_estimates").insert({
        "fiscal_year_id": anno_id, "category_id": categoria["id"],
        "estimated_gross_amount": "500.00", "amount_includes_vat": True,
        "notes": NOTA_TEST,
    }).execute()
    if len(r.data or []) != 1:
        raise RuntimeError("Stima non confermata")


def mostra_manutenzione(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Manutenzione auto · prova annuale")
    st.caption("La cifra annuale di 500 € riproduce il foglio, non è una spesa realmente sostenuta.")
    try:
        categoria = _categoria(client, anno["id"])
        stima = _stima(client, anno["id"], categoria["id"]) if categoria else None
    except Exception:
        st.error("Impossibile leggere la manutenzione. Nessun dato modificato.")
        return
    if stima:
        lordo = Decimal(str(stima["estimated_gross_amount"]))
        iva, _iva_detraibile, netto, deducibile = _calcola(
            lordo, categoria, bool(stima["amount_includes_vat"])
        )
        if stima.get("notes") == NOTA_TEST:
            st.warning("MANUTENZIONE DI PROVA: deducibilità e detraibilità sono quelle del foglio, non parametri fiscali verificati.")
        st.dataframe([{
            "Costo lordo": _euro_arrotondato(lordo), "IVA scorporata": _euro_arrotondato(iva),
            "Costo netto": _euro_arrotondato(netto),
            "Quota deducibile": _euro_arrotondato(deducibile),
        }], hide_index=True, use_container_width=True)
    elif anno["status"] == "open":
        if st.button("Carica manutenzione auto di prova da 500 €", key="manut_carica"):
            try:
                _carica(client, anno["id"])
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Caricamento non confermato: controlla prima di riprovare.")
            else:
                st.rerun()
    else:
        st.info("Nessuna manutenzione annuale registrata.")
    if anno["status"] == "open" and stima and stima.get("notes") == NOTA_TEST:
        with st.expander("Elimina manutenzione di prova"):
            ok = st.checkbox("Confermo l'eliminazione della manutenzione di prova", key="manut_ok")
            if st.button("Elimina manutenzione di prova", key="manut_elimina", disabled=not ok):
                try:
                    r = (client.table("annual_cost_estimates").delete()
                         .eq("id", stima["id"]).eq("fiscal_year_id", anno["id"])
                         .eq("notes", NOTA_TEST).execute())
                    if len(r.data or []) != 1:
                        raise RuntimeError("Eliminazione non confermata")
                except Exception:
                    st.error("Eliminazione non confermata: controlla i dati.")
                else:
                    st.rerun()
