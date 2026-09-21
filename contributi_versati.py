"""Registro dei contributi documentati, distinto da stime e deduzioni generiche.

Usa la tabella tax_deductions ESISTENTE senza migrazioni. I record con note
CONTRIBUTI_VERSATI_V1|TIPO|ANNO_COMPETENZA sono soltanto dati dichiarati
inseriti dall'utente; NON sono automaticamente deduzioni fiscalmente ammesse.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

import streamlit as st
from supabase import Client

from fatturato import euro

D = Decimal
CENT = D("0.01")
PREFISSO = "CONTRIBUTI_VERSATI_V1|"
TIPI = {"INPS": "INPS · versamento documentato", "ENASARCO": "Enasarco · quota personale trattenuta/documentata"}


def e_contributo(record: dict) -> bool:
    """Identifica un record riservato anche quando i metadati sono danneggiati."""
    return str(record.get("notes") or "").startswith(PREFISSO)


def dati_contributo(record: dict) -> tuple[str, int]:
    note = str(record.get("notes") or "")
    campi = note.split("|")
    if len(campi) != 3 or campi[0] != PREFISSO[:-1] or campi[1] not in TIPI:
        raise ValueError("Metadati di un contributo non leggibili; non modificare la registrazione.")
    try:
        competenza = int(campi[2])
    except (TypeError, ValueError) as exc:
        raise ValueError("Anno di competenza del contributo non valido.") from exc
    if not 2000 <= competenza <= 2100:
        raise ValueError("Anno di competenza del contributo fuori intervallo.")
    return campi[1], competenza


def _importo(testo: str) -> D:
    s = str(testo).strip().replace("€", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        valore = D(s)
    except InvalidOperation as exc:
        raise ValueError("Inserisci un importo valido (es. 4611,64).") from exc
    if (not valore.is_finite() or valore <= 0 or valore > D("999999999999.99")
            or valore != valore.quantize(CENT)):
        raise ValueError("L'importo deve essere maggiore di zero e avere al massimo due decimali.")
    return valore


def _verifica(anno: int, tipo: str, competenza: int, pagamento: date,
              importo: D, causale: str) -> tuple[str, str]:
    descrizione = " ".join(causale.split())
    if not descrizione or len(descrizione) > 200:
        raise ValueError("Inserisci una causale da 1 a 200 caratteri.")
    if tipo not in TIPI or not 2000 <= competenza <= anno:
        raise ValueError("Tipo o anno di competenza non valido.")
    if pagamento.year != anno:
        raise ValueError(f"La data del versamento deve appartenere al {anno} selezionato.")
    if pagamento > date.today():
        raise ValueError("Non registrare come già effettuato un pagamento con data futura.")
    if importo <= 0:
        raise ValueError("L'importo deve essere positivo.")
    return descrizione, f"{PREFISSO}{tipo}|{competenza}"


def _leggi(client: Client, anno: dict) -> list[dict]:
    from registri import leggi_tutti
    return [r for r in leggi_tutti(client, "tax_deductions", fiscal_year_id=anno["id"]) if e_contributo(r)]


def _salva(client: Client, anno: dict, esistenti: list[dict], *,
           tipo: str, competenza: int, pagamento: date, importo: D,
           causale: str, modifica: dict | None = None) -> None:
    descrizione, note = _verifica(int(anno["fiscal_year"]), tipo, competenza,
                                 pagamento, importo, causale)
    for r in esistenti:
        if modifica and r["id"] == modifica["id"]:
            continue
        if (r["description"] == descrizione and str(r["payment_date"]) == pagamento.isoformat()
                and D(str(r["amount"])) == importo and r["notes"] == note):
            raise ValueError("Versamento identico già registrato: verifica prima di inserirlo nuovamente.")
    dati = {"description": descrizione, "amount": str(importo),
            "payment_date": pagamento.isoformat(), "notes": note}
    if modifica:
        risposta = (client.table("tax_deductions").update(dati)
                    .eq("id", modifica["id"]).eq("fiscal_year_id", anno["id"])
                    .eq("notes", modifica["notes"]).execute())
    else:
        risposta = client.table("tax_deductions").insert({
            "fiscal_year_id": anno["id"], **dati,
        }).execute()
    if len(risposta.data or []) != 1:
        raise RuntimeError("Salvataggio non confermato: controlla il registro prima di riprovare.")


def _elimina(client: Client, anno: dict, record: dict) -> None:
    risposta = (client.table("tax_deductions").delete()
                .eq("id", record["id"]).eq("fiscal_year_id", anno["id"])
                .eq("notes", record["notes"]).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata: ricontrolla il registro.")


def mostra_contributi_versati(client: Client, anno: dict) -> None:
    anno_num = int(anno["fiscal_year"])
    st.divider()
    st.markdown(f"### 4 · Contributi versati o trattenuti · {anno_num}")
    st.caption("Registra solo pagamenti INPS realmente eseguiti o trattenute Enasarco documentate. "
               "L'anno di competenza può essere precedente all'anno del pagamento.")
    st.warning("Queste sono registrazioni dichiarate, NON deduzioni fiscali approvate. "
               "Alimentano soltanto lo scenario a cassa del Conto economico; "
               "non si sommano alle altre deduzioni della scheda.")
    try:
        righe = _leggi(client, anno)
        arricchite = [(r, *dati_contributo(r)) for r in righe]
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere i contributi. Nessun dato modificato.")
        return
    inps = sum((D(str(r["amount"])) for r, tipo, _ in arricchite if tipo == "INPS"), D("0"))
    enasarco = sum((D(str(r["amount"])) for r, tipo, _ in arricchite if tipo == "ENASARCO"), D("0"))
    precedenti = sum((D(str(r["amount"])) for r, tipo, competenza in arricchite
                     if tipo == "INPS" and competenza < anno_num), D("0"))
    c1, c2, c3 = st.columns(3)
    c1.metric("INPS documentato nell'anno", euro(inps))
    c2.metric("Di cui INPS anni precedenti", euro(precedenti))
    c3.metric("Enasarco documentato nell'anno", euro(enasarco))
    if arricchite:
        st.dataframe([{
            "Tipo": TIPI[tipo], "Competenza": competenza,
            "Data": r["payment_date"], "Causale": r["description"],
            "Importo": euro(D(str(r["amount"]))),
        } for r, tipo, competenza in arricchite], hide_index=True, width="stretch")
    else:
        st.info("Nessun contributo documentato registrato per l'anno selezionato.")
    if anno["status"] != "open":
        st.info("Anno fiscale chiuso: registro in sola lettura.")
        return
    with st.expander("➕ Registra un versamento o una trattenuta documentata"):
        with st.form(f"contributo_new_{anno_num}", clear_on_submit=True):
            tipo = st.selectbox("Tipo", list(TIPI), format_func=lambda k: TIPI[k])
            competenza = st.number_input("Anno di competenza", min_value=2000,
                                         max_value=anno_num, value=anno_num, step=1)
            pagamento = st.date_input("Data del pagamento o della trattenuta documentata",
                                      value=date(anno_num, 1, 1), format="DD/MM/YYYY")
            causale = st.text_input("Causale (es. INPS saldo 2026)")
            importo = st.text_input("Importo (€)", placeholder="es. 4611,64")
            conferma = st.checkbox("Confermo che il versamento o la trattenuta è già avvenuto ed è documentato")
            salva = st.form_submit_button("Salva contributo")
        if salva:
            try:
                if not conferma:
                    raise ValueError("Conferma prima l'avvenuto pagamento o trattenuta.")
                _salva(client, anno, righe, tipo=tipo, competenza=int(competenza),
                       pagamento=pagamento, importo=_importo(importo), causale=causale)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Salvataggio non confermato: controlla il registro prima di riprovare.")
            else:
                st.rerun()
    if not arricchite:
        return
    with st.expander("Modifica o elimina un contributo registrato"):
        opzioni = {r["id"]: (r, tipo, competenza) for r, tipo, competenza in arricchite}
        scelto = st.selectbox("Contributo da modificare", list(opzioni),
                             format_func=lambda k: f"{opzioni[k][0]['payment_date']} · {opzioni[k][0]['description']} · {euro(D(str(opzioni[k][0]['amount'])))}",
                             key=f"contributo_scelto_{anno_num}")
        r, tipo_attuale, anno_comp = opzioni[scelto]
        with st.form(f"contributo_edit_{scelto}"):
            tipo = st.selectbox("Tipo", list(TIPI), index=list(TIPI).index(tipo_attuale),
                                format_func=lambda k: TIPI[k])
            competenza = st.number_input("Anno di competenza", min_value=2000,
                                         max_value=anno_num, value=anno_comp, step=1)
            pagamento = st.date_input("Data del pagamento o della trattenuta",
                                      value=date.fromisoformat(str(r["payment_date"])), format="DD/MM/YYYY")
            causale = st.text_input("Causale", value=r["description"])
            importo = st.text_input("Importo (€)", value=str(r["amount"]).replace(".", ","))
            elimina = st.checkbox("Elimina definitivamente questa registrazione")
            conferma = st.checkbox("Confermo i dati e l'operazione richiesta")
            salva = st.form_submit_button("Conferma operazione")
        if salva:
            try:
                if not conferma:
                    raise ValueError("Conferma prima l'operazione.")
                if elimina:
                    _elimina(client, anno, r)
                else:
                    _salva(client, anno, righe, tipo=tipo, competenza=int(competenza),
                           pagamento=pagamento, importo=_importo(importo),
                           causale=causale, modifica=r)
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Operazione non confermata: ricontrolla il registro prima di riprovare.")
            else:
                st.rerun()
