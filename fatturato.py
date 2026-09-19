"""Fatturato IVA esclusa: solo importi registrati, nessuna previsione inserita a mano.

La proiezione riproduce il foglio originale: per ciascuna mandante,
SUM(mesi compilati) / COUNT(mesi compilati) * 12. Un mese mancante
non equivale a zero; uno zero salvato esplicitamente conta come mese.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st
from supabase import Client

MESI = (
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
)
CENT = Decimal("0.01")
NOTA_TEST = "DATI DI PROVA - confronto con foglio originale, gennaio 2027"
# Numeri inseriti dall'utente nelle quattro celle di gennaio del foglio originale.
ESEMPIO_GENNAIO = {
    "innovagroup caino": "7000.00",
    "innovagroup borgo": "1000.00",
    "innovagroup erbe": "1100.00",
    "innovagroup fontanella": "500.00",
}


def euro(importo: Decimal) -> str:
    """Formatta un Decimal con le convenzioni italiane."""
    return f"{importo:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".") + " €"


def importo_valido(testo: str) -> Decimal:
    """Accetta 7000,00 / 7.000,00 / 7000.00, con massimo due decimali."""
    testo = testo.strip().replace(" ", "")
    if not testo:
        raise ValueError("Inserisci un importo; per un mese senza fatturato scrivi 0.")
    if "," in testo:
        testo = testo.replace(".", "").replace(",", ".")
    try:
        valore = Decimal(testo)
    except InvalidOperation as exc:
        raise ValueError("Importo non valido. Esempio: 7000,00.") from exc
    if not valore.is_finite() or valore < 0 or valore > Decimal("999999999999.99"):
        raise ValueError("Inserisci un importo non negativo e finito.")
    if valore != valore.quantize(CENT):
        raise ValueError("Utilizza al massimo due cifre decimali.")
    return valore.quantize(CENT)


def riepilogo(mandanti: list[dict], righe: list[dict]) -> tuple[list[dict], Decimal, Decimal | None]:
    """Calcolo puro: un mese con importo zero conta come mese compilato."""
    per_mandante = {item["id"]: [] for item in mandanti}
    for riga in righe:
        if riga["principal_id"] in per_mandante:
            per_mandante[riga["principal_id"]].append(Decimal(str(riga["amount"])))
    risultati = []
    totale = Decimal("0")
    stima_totale = Decimal("0")
    almeno_un_mese = False
    for mandante in mandanti:
        valori = per_mandante[mandante["id"]]
        maturato = sum(valori, Decimal("0"))
        media = maturato / len(valori) if valori else None
        stima = media * 12 if media is not None else None
        totale += maturato
        if stima is not None:
            stima_totale += stima
            almeno_un_mese = True
        risultati.append({
            "nome": mandante["name"], "mesi": len(valori),
            "totale": maturato, "media": media, "stima": stima,
        })
    return risultati, totale, stima_totale if almeno_un_mese else None


def leggi_fatturato(client: Client, anno_id: str) -> list[dict]:
    risposta = (
        client.table("monthly_revenues")
        .select("id,principal_id,month,amount,notes")
        .eq("fiscal_year_id", anno_id)
        .order("month")
        .execute()
    )
    return risposta.data or []


def salva_fatturato(
    client: Client, anno_id: str, mandante_id: str, mese: int, importo: Decimal,
    esistente: dict | None,
) -> None:
    if mese not in range(1, 13):
        raise ValueError("Mese non valido.")
    if esistente is not None:
        # Modificare un esempio lo trasforma in dato ordinario, togliendo l'etichetta TEST.
        risposta = (
            client.table("monthly_revenues")
            .update({"amount": str(importo), "notes": None})
            .eq("id", esistente["id"])
            .eq("fiscal_year_id", anno_id)
            .eq("principal_id", mandante_id)
            .execute()
        )
    else:
        risposta = (
            client.table("monthly_revenues")
            .insert({
                "fiscal_year_id": anno_id, "principal_id": mandante_id,
                "month": mese, "amount": str(importo),
            })
            .execute()
        )
    if len(risposta.data or []) != 1:
        raise RuntimeError("Salvataggio non confermato")


def elimina_fatturato(client: Client, anno_id: str, riga_id: str) -> None:
    risposta = (
        client.table("monthly_revenues")
        .delete().eq("id", riga_id).eq("fiscal_year_id", anno_id).execute()
    )
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata")


def carica_esempio(client: Client, anno_id: str, mandanti: list[dict]) -> None:
    """Inserisce quattro record TEST solo se l'anno e' completamente vuoto."""
    if leggi_fatturato(client, anno_id):
        raise ValueError("Sono già presenti fatturati: nessun dato di prova inserito.")
    indice = {item["name"].strip().casefold(): item["id"] for item in mandanti}
    if any(nome not in indice for nome in ESEMPIO_GENNAIO):
        raise ValueError("Registra prima tutte e quattro le mandanti del foglio.")
    righe = [
        {
            "fiscal_year_id": anno_id,
            "principal_id": indice[nome],
            "month": 1,
            "amount": importo,
            "notes": NOTA_TEST,
        }
        for nome, importo in ESEMPIO_GENNAIO.items()
    ]
    risposta = client.table("monthly_revenues").insert(righe).execute()
    if len(risposta.data or []) != 4:
        raise RuntimeError("Caricamento non confermato: ricontrolla le righe prima di riprovare")


def mostra_fatturato(client: Client, anno: dict, mandanti: list[dict]) -> None:
    st.divider()
    st.subheader("Fatturato registrato · 2027")
    st.caption("Importi fatturati, IVA esclusa. La stima è calcolata automaticamente: non si inseriscono previsioni.")
    if not mandanti:
        st.info("Aggiungi prima una mandante.")
        return
    try:
        righe = leggi_fatturato(client, anno["id"])
    except Exception:
        st.error("Impossibile leggere i fatturati. Nessun dato modificato.")
        return
    test_presenti = any(r.get("notes") == NOTA_TEST for r in righe)
    if test_presenti:
        st.warning("DATI DI PROVA PRESENTI: i risultati qui sotto NON rappresentano il tuo fatturato reale. Elimina manualmente le righe di prova prima di iniziare.")

    risultati, maturato, proiezione = riepilogo(mandanti, righe)
    c1, c2 = st.columns(2)
    c1.metric("Fatturato registrato", euro(maturato))
    c2.metric("Stima a fine anno", euro(proiezione.quantize(CENT, rounding=ROUND_HALF_UP)) if proiezione is not None else "—")
    st.caption("Stima per mandante = totale dei mesi compilati ÷ numero di mesi compilati × 12; un mese vuoto non è uno zero. È una proiezione matematica, non un fatturato acquisito.")

    indice = {(r["principal_id"], int(r["month"])): r for r in righe}
    tabella = []
    for mese in range(1, 13):
        riga = {"Mese": MESI[mese - 1]}
        totale_mese = Decimal("0")
        for mandante in mandanti:
            dato = indice.get((mandante["id"], mese))
            valore = Decimal(str(dato["amount"])) if dato else None
            riga[mandante["name"]] = euro(valore) if valore is not None else "—"
            if valore is not None:
                totale_mese += valore
        riga["Totale mese"] = euro(totale_mese) if any(int(r["month"]) == mese for r in righe) else "—"
        tabella.append(riga)
    st.dataframe(tabella, hide_index=True, use_container_width=True)
    st.markdown("**Riepilogo per mandante**")
    st.dataframe(
        [{
            "Mandante": dato["nome"], "Mesi compilati": dato["mesi"],
            "Fatturato": euro(dato["totale"]),
            "Media mesi compilati": euro(dato["media"].quantize(CENT, rounding=ROUND_HALF_UP)) if dato["media"] is not None else "—",
            "Stima annua": euro(dato["stima"].quantize(CENT, rounding=ROUND_HALF_UP)) if dato["stima"] is not None else "—",
        } for dato in risultati], hide_index=True, use_container_width=True,
    )
    if len(righe) == 4 and all(r.get("notes") == NOTA_TEST and int(r["month"]) == 1 for r in righe):
        st.info("Confronto con il foglio originale: fatturato gennaio **9.600,00 €**; stima annua **115.200,00 €**. Sono importi di prova; il conto economico completo sarà confrontabile solo dopo aver configurato anche costi, contributi e imposte.")

    if anno["status"] != "open":
        st.info("Anno chiuso: fatturati in sola lettura.")
        return

    if not righe and len(mandanti) >= 4:
        with st.expander("Carica i quattro valori di prova dal foglio originale", expanded=True):
            st.write("Gennaio: Caino 7.000 €, Borgo 1.000 €, Erbe 1.100 €, Fontanella 500 €. Non verrà letto o modificato il foglio Google.")
            if st.button("Carica dati di prova gennaio", type="primary"):
                try:
                    carica_esempio(client, anno["id"], mandanti)
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("Caricamento non confermato: verifica la tabella prima di riprovare.")
                else:
                    st.rerun()

    st.markdown("**Inserisci o modifica un mese**")
    nomi = {item["name"]: item["id"] for item in mandanti}
    nome = st.selectbox("Mandante", list(nomi), key="fatturato_mandante")
    mese_nome = st.selectbox("Mese", MESI, key="fatturato_mese")
    mese = MESI.index(mese_nome) + 1
    esistente = indice.get((nomi[nome], mese))
    if esistente:
        st.caption("Mese già registrato: salvando sostituisci il valore esistente. Se era un dato di prova, verrà contrassegnato come dato ordinario.")
    with st.form("salva_fatturato"):
        testo = st.text_input(
            "Importo fatturato (IVA esclusa)",
            value=str(esistente["amount"]).replace(".", ",") if esistente else "",
            help="Usa 7000,00; per un mese a zero inserisci 0. Lasciare un mese vuoto significa non averlo ancora compilato.",
        )
        salva = st.form_submit_button("Salva importo", type="primary")
    if salva:
        try:
            importo = importo_valido(testo)
            salva_fatturato(client, anno["id"], nomi[nome], mese, importo, esistente)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Salvataggio non confermato: verifica la tabella prima di riprovare.")
        else:
            st.rerun()

    if righe:
        with st.expander("Elimina manualmente un importo"):
            mandanti_per_id = {m["id"]: m["name"] for m in mandanti}
            opzioni = {
                f"{MESI[int(r['month']) - 1]} · {mandanti_per_id.get(r['principal_id'], 'Mandante')} · {euro(Decimal(str(r['amount'])))}" +
                (" · TEST" if r.get("notes") == NOTA_TEST else "") + f" · {r['id'][:8]}": r["id"]
                for r in righe
            }
            selezione = st.selectbox("Importo da eliminare", list(opzioni))
            conferma = st.checkbox("Confermo l'eliminazione definitiva di questa riga")
            if st.button("Elimina importo", disabled=not conferma):
                try:
                    elimina_fatturato(client, anno["id"], opzioni[selezione])
                except Exception:
                    st.error("Eliminazione non confermata: verifica la tabella prima di riprovare.")
                else:
                    st.rerun()
