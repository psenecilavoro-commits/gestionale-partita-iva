"""Tabella accantonamenti con provvigioni nette manuali e persistenti.

Le provvigioni nette sono distinte dal fatturato e dalle riserve; la
differenza non costituisce denaro disponibile o netto fiscale.
"""
from decimal import Decimal

import streamlit as st
from supabase import Client

from accantonamenti import leggi_accantonamenti, salva_accantonamento, elimina_accantonamento
from fatturato import CENT, MESI, NOTA_TEST, euro, importo_valido, leggi_fatturato

TABELLA_NETTE = "monthly_net_commissions"


def leggi_provvigioni_nette(client: Client, anno_id: str) -> list[dict]:
    risultato = (client.table(TABELLA_NETTE).select("id,month,amount")
                 .eq("fiscal_year_id", anno_id).order("month").execute())
    return risultato.data or []


def salva_provvigione_netta(client: Client, anno_id: str, mese: int,
                            importo: Decimal, esistente: dict | None) -> None:
    if mese not in range(1, 13) or not importo.is_finite() or importo < 0 or importo != importo.quantize(CENT):
        raise ValueError("Mese o importo non valido.")
    if esistente is None:
        risposta = client.table(TABELLA_NETTE).insert({
            "fiscal_year_id": anno_id, "month": mese, "amount": str(importo),
        }).execute()
    else:
        risposta = (client.table(TABELLA_NETTE).update({"amount": str(importo)})
                    .eq("id", esistente["id"]).eq("fiscal_year_id", anno_id)
                    .eq("month", mese).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Salvataggio non confermato.")


def elimina_provvigione_netta(client: Client, anno_id: str, esistente: dict) -> None:
    risposta = (client.table(TABELLA_NETTE).delete().eq("id", esistente["id"])
                .eq("fiscal_year_id", anno_id).eq("month", esistente["month"]).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata.")


def _ricavi_per_mese(fatturati: list[dict]) -> dict[int, Decimal]:
    per_mese: dict[int, Decimal] = {}
    for riga in fatturati:
        mese = int(riga["month"])
        if mese not in range(1, 13):
            raise ValueError("Mese fatturato non valido.")
        per_mese[mese] = per_mese.get(mese, Decimal("0")) + Decimal(str(riga["amount"]))
    return per_mese


def calcola_tabella_completa(fatturati: list[dict], riserve: list[dict],
                             nette: list[dict]) -> tuple[list[dict], Decimal, Decimal, Decimal, int]:
    """Non inventa zeri per mesi privi di registrazioni."""
    ricavi = _ricavi_per_mese(fatturati)
    per_riserva: dict[int, Decimal] = {}
    per_nette: dict[int, Decimal] = {}
    for gruppo, destinazione, campo in (
        (riserve, per_riserva, "reserved_amount"),
        (nette, per_nette, "amount"),
    ):
        for riga in gruppo:
            mese = int(riga["month"])
            if mese not in range(1, 13) or mese in destinazione:
                raise ValueError("Mese duplicato o non valido nella tabella mensile.")
            destinazione[mese] = Decimal(str(riga[campo]))
    righe = []
    parziale = Decimal("0")
    completi = 0
    for mese, nome in enumerate(MESI, start=1):
        fatturato = ricavi.get(mese)
        netta = per_nette.get(mese)
        riserva = per_riserva.get(mese)
        diff = netta - riserva if netta is not None and riserva is not None else None
        if diff is not None:
            parziale += diff
            completi += 1
        righe.append({
            "Mese": nome,
            "Fatturato IVA esclusa": euro(fatturato) if fatturato is not None else "—",
            "Provvigioni nette · manuale": euro(netta) if netta is not None else "—",
            "Accantonato · manuale": euro(riserva) if riserva is not None else "—",
            "Provv. nette − accantonato · prima IVA": euro(diff) if diff is not None else "—",
        })
    return (righe, sum(per_nette.values(), Decimal("0")),
            sum(per_riserva.values(), Decimal("0")), parziale, completi)


def _tabella_non_disponibile(exc: Exception) -> bool:
    codice = str(getattr(exc, "code", ""))
    messaggio = str(exc).lower()
    return codice in ("PGRST205", "42P01") or (
        "monthly_net_commissions" in messaggio
        and ("schema cache" in messaggio or "does not exist" in messaggio)
    )


def mostra_accantonamenti(client: Client, anno: dict) -> None:
    st.subheader("Tabella accantonamenti")
    st.caption("«Provvigioni nette» è un importo inserito da te e separato dal Fatturato. "
               "Nessuna provvigione netta viene calcolata automaticamente.")
    try:
        fatturati = leggi_fatturato(client, anno["id"])
        riserve = leggi_accantonamenti(client, anno["id"])
    except Exception:
        st.error("Impossibile leggere fatturato o accantonamenti. Nessun dato modificato.")
        return
    nette_disponibili = True
    try:
        nette = leggi_provvigioni_nette(client, anno["id"])
    except Exception as exc:
        nette = []
        nette_disponibili = False
        if _tabella_non_disponibile(exc):
            st.warning("La colonna Provvigioni nette è pronta, ma per salvarne i valori "
                       "devi eseguire una sola volta SQL_PROVVIGIONI_NETTE.sql nel SQL Editor "
                       "del Supabase dedicato al Gestionale Partita IVA; poi aggiorna con F5.")
            st.link_button("Apri lo script SQL su GitHub", "https://github.com/psenecilavoro-commits/gestionale-partita-iva/blob/main/SQL_PROVVIGIONI_NETTE.sql")
        else:
            st.error("Impossibile leggere le provvigioni nette: controlla permessi e connessione. "
                     "Non inserire valori finché l'accesso non è ripristinato.")
    if any(r.get("notes") == NOTA_TEST for r in fatturati):
        st.warning("Il Fatturato contiene dati di prova; non sono provvigioni nette reali.")
    try:
        tabella, totale_nette, totale_riserve, residuo_parziale, completi = calcola_tabella_completa(
            fatturati, riserve, nette,
        )
    except (ValueError, ArithmeticError):
        st.error("La tabella contiene mesi duplicati o importi non validi. Nessun dato modificato.")
        return
    st.dataframe(tabella, hide_index=True, width="stretch", height="content")
    c1, c2, c3 = st.columns(3)
    c1.metric("Provvigioni nette inserite", euro(totale_nette) if nette_disponibili else "—")
    c2.metric("Accantonamenti annotati", euro(totale_riserve))
    c3.metric("Differenza parziale · mesi completi", euro(residuo_parziale) if nette_disponibili and completi else "—")
    if int(anno["fiscal_year"]) == 2026:
        st.caption(
            f"Mesi con nette e accantonamenti compilati: {completi}/12. "
            "La differenza non rappresenta il netto disponibile: contributi, Enasarco, "
            "imposta sostitutiva e costi restano separati. Un mese vuoto non equivale a zero."
        )
        st.info(
            "Per il 2026 in regime forfettario gli accantonamenti sono un controllo di cassa; "
            "non viene costruita una liquidazione IVA ordinaria."
        )
    else:
        st.caption(f"Mesi con nette e accantonamenti compilati: {completi}/12. "
                   "La differenza è PRIMA dell'IVA dovuta e non rappresenta il netto disponibile. "
                   "Un mese vuoto non equivale a zero; annotare un accantonamento non sposta denaro.")
        st.info("Il netto mensile ipotetico è visibile nel quadro mensile, ma non rappresenta "
                "il denaro disponibile. Le liquidazioni IVA documentali sono separate e da verificare.")
    if anno["status"] != "open":
        st.info("Anno chiuso: dati in sola lettura.")
        return
    indice_nette = {int(r["month"]): r for r in nette}
    indice_riserve = {int(r["month"]): r for r in riserve}
    mese_nome = st.selectbox("Mese da compilare", MESI, key="accantonamenti_mese")
    mese = MESI.index(mese_nome) + 1
    st.markdown("#### Inserisci o modifica le provvigioni nette")
    if nette_disponibili:
        presente = indice_nette.get(mese)
        with st.form(f"provvigioni_nette_form_{anno['id']}_{mese}"):
            testo = st.text_input(
                "Provvigioni nette del mese (€)",
                value=str(presente["amount"]).replace(".", ",") if presente else "",
                help="Inserisci l'importo del mese: non viene ricavato dal fatturato.",
            )
            salva = st.form_submit_button("Salva provvigioni nette", type="primary")
        if salva:
            try:
                salva_provvigione_netta(client, anno["id"], mese,
                                        importo_valido(testo), presente)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Salvataggio non confermato: controlla la riga prima di riprovare.")
            else:
                st.rerun()
        if presente is not None:
            conferma_nette = st.checkbox("Confermo l'eliminazione della provvigione netta di questo mese",
                                         key=f"nette_elimina_ok_{anno['id']}_{mese}")
            if st.button("Elimina provvigioni nette del mese", disabled=not conferma_nette,
                         key=f"nette_elimina_btn_{anno['id']}_{mese}"):
                try:
                    elimina_provvigione_netta(client, anno["id"], presente)
                except Exception:
                    st.error("Eliminazione non confermata: controlla la tabella.")
                else:
                    st.rerun()
    else:
        st.caption("Inserimento disattivato finché la nuova tabella non è accessibile.")
    st.markdown("#### Aggiungi o modifica un accantonamento")
    presente_riserva = indice_riserve.get(mese)
    with st.form(f"accantonamento_form_{mese}"):
        importo_testo = st.text_input(
            "Importo accantonato (€)",
            value=str(presente_riserva["reserved_amount"]).replace(".", ",") if presente_riserva else "",
            help="0 è ammesso solo se inserito intenzionalmente.",
        )
        nota = st.text_input("Nota facoltativa",
                             value=(presente_riserva.get("notes") or "") if presente_riserva else "")
        invia = st.form_submit_button("Salva accantonamento", type="primary")
    if invia:
        try:
            salva_accantonamento(client, anno["id"], mese,
                                 importo_valido(importo_testo), nota, presente_riserva)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Salvataggio non confermato. Controlla la riga prima di riprovare.")
        else:
            st.rerun()
    if presente_riserva is not None:
        conferma = st.checkbox("Confermo l'eliminazione dell'accantonamento di questo mese",
                               key=f"accantonamenti_elimina_ok_{anno['id']}_{mese}")
        if st.button("Elimina accantonamento del mese", disabled=not conferma,
                     key=f"accantonamenti_elimina_btn_{anno['id']}_{mese}"):
            try:
                elimina_accantonamento(client, anno["id"], presente_riserva)
            except Exception:
                st.error("Eliminazione non confermata. Controlla la riga prima di riprovare.")
            else:
                st.rerun()
