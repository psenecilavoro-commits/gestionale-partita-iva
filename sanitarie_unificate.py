"""Vista unificata delle spese sanitarie, senza migrazioni o modifiche dati.

Registrazioni manuali e registro OCR restano separati. La franchigia
matematica e' applicata una sola volta al totale dell'anno.
"""
from decimal import Decimal
from hashlib import sha256

import streamlit as st
from supabase import Client

import detrazioni_deduzioni as dd
import sanitarie_documenti as sd
from contributi_versati import e_contributo
from fatturato import euro

D = Decimal
ALIQUOTA_FOGLIO = D("0.19")


def _sanitaria(r: dict) -> bool:
    return str(r.get("notes") or "").startswith("TIPO_SANITARIE_FOGLIO")


def _riepilogo(crediti: list[dict], anno: int) -> tuple[D, D, list[dict], list[dict]]:
    registro = sd._trova_aggregato(crediti, anno)
    documenti = D(str(registro["original_amount"])) if registro else D("0")
    manuali = D("0")
    anomalie = []
    altre = []
    for r in crediti:
        numero = dd._numero_rata(anno, int(r["first_fiscal_year"]), int(r["installment_count"]))
        if numero is None:
            continue
        if r["description"] == sd.DESCRIZIONE:
            if registro is None or r["id"] != registro["id"]:
                anomalie.append(r)
            continue
        if _sanitaria(r):
            if int(r["installment_count"]) != 1 or D(str(r["credit_rate"])) != ALIQUOTA_FOGLIO:
                anomalie.append(r)
            else:
                manuali += D(str(r["original_amount"]))
        else:
            altre.append(r)
    return manuali, documenti, anomalie, altre


def _carica_documenti(client: Client, anno: dict, crediti: list[dict], manuali: D) -> None:
    anno_num = int(anno["fiscal_year"])
    st.markdown("#### Carica scontrini farmacia e ricevute mediche")
    st.caption("PDF, JPG o PNG: massimo 10 documenti da 8 MB. I documenti sono letti "
               "sul server, ma non vengono conservati nel database.")
    notifica = st.session_state.pop(f"san_notifica_{anno_num}", None)
    if notifica:
        st.success(notifica)
    if anno["status"] != "open":
        st.info("Anno fiscale chiuso: non si possono aggiungere documenti.")
        return
    try:
        registro = sd._trova_aggregato(crediti, anno_num)
        precedenti = sd._hash_presenti(registro["notes"]) if registro else set()
    except ValueError as exc:
        st.error(str(exc))
        return
    caricati = st.file_uploader("Carica uno o più documenti", type=["pdf", "jpg", "jpeg", "png"],
                               accept_multiple_files=True, key=f"san_documenti_{anno_num}")
    if not caricati:
        return
    if len(caricati) > sd.MAX_FILES:
        st.warning(f"Seleziona al massimo {sd.MAX_FILES} documenti alla volta.")
        return
    nuovi = {}
    cache = st.session_state.setdefault(f"san_cache_{anno_num}", {})
    ripetuti = 0
    errori = []
    for documento in caricati:
        dati = documento.getvalue()
        impronta = sha256(dati).hexdigest()
        if impronta in precedenti or impronta in nuovi:
            ripetuti += 1
            continue
        if impronta not in cache:
            try:
                testo = sd._leggi_documento(documento.name, dati)
                proposto = sd.suggerisci_importo(testo)
                cache[impronta] = str(proposto) if proposto is not None else ""
            except Exception:
                cache[impronta] = ""
                errori.append(documento.name)
        nuovi[impronta] = (documento.name, cache[impronta])
    if ripetuti:
        st.info(f"{ripetuti} file identici già acquisiti o ripetuti: non saranno conteggiati di nuovo.")
    if not nuovi:
        return
    st.caption(f"{len(nuovi)} documenti nuovi da controllare; nessun salvataggio prima della conferma.")
    if errori:
        st.warning("Lettura automatica non riuscita: controlla e inserisci manualmente l'importo.")
    valori = {}
    with st.expander("Controlla o correggi gli importi", expanded=bool(errori)):
        for impronta, (nome, proposto) in nuovi.items():
            valori[impronta] = st.text_input(
                f"{nome} · importo (€)", value=proposto.replace(".", ",") if proposto else "",
                key=f"san_importo_{anno_num}_{impronta}", placeholder="es. 12,50",
            )
    try:
        importi_validi = {h: sd._valore(v) for h, v in valori.items()}
    except ValueError:
        importi_validi = {}
    somma = sum(importi_validi.values(), D("0")) if len(importi_validi) == len(nuovi) else None
    st.metric("Totale nuovo da aggiungere", euro(somma) if somma is not None else "Da completare")
    selezione = sha256("".join(sorted(nuovi)).encode()).hexdigest()[:12]
    verifica = st.checkbox(f"Ho controllato importi e anno {anno_num}; confermo la somma.",
                           key=f"san_verifica_{anno_num}_{selezione}")
    non_duplicati = True
    if manuali > 0:
        st.warning("Esistono spese sanitarie inserite a mano. Verifica che questi "
                   "documenti NON siano già inclusi in quelle registrazioni: "
                   "due foto diverse o un inserimento manuale dello stesso scontrino potrebbero duplicarsi.")
        non_duplicati = st.checkbox("Confermo che questi documenti non sono già compresi nelle spese manuali.",
                                   key=f"san_no_doppioni_manual_{anno_num}_{selezione}")
    if st.button("Conferma e aggiungi alle spese sanitarie", type="primary",
                 key=f"san_conferma_{anno_num}"):
        if not verifica or not non_duplicati:
            st.warning("Conferma importi, anno e assenza di doppioni prima di salvare.")
            return
        try:
            importi = {h: sd._valore(v) for h, v in valori.items()}
            numero, aggiunta, _ = sd._salva(client, anno_num, importi)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Salvataggio non confermato: aggiorna e controlla il totale prima di riprovare.")
        else:
            st.session_state[f"san_notifica_{anno_num}"] = (
                f"{numero} documenti acquisiti · aggiunti {euro(aggiunta)} al totale sanitario."
            )
            st.rerun()


def mostra_detrazioni_unificate(client: Client, anno: dict) -> None:
    anno_num = int(anno["fiscal_year"])
    st.subheader("Detrazioni e deduzioni")
    st.warning("Le formule sono scenari matematici, NON parametri fiscali verificati per il 2027. "
               "Questi importi non modificano ancora imposte o netto.")
    st.info("Le rate pluriennali avanzano con l'anno selezionato e scompaiono "
            "dalla vista annuale dopo l'ultima rata; lo storico resta conservato.")
    try:
        crediti, deduzioni = dd._leggi(client, anno)
        manuali, documenti, anomalie, altre = _riepilogo(crediti, anno_num)
    except ValueError as exc:
        st.error(f"Riepilogo sanitario non disponibile: {exc} Nessun dato modificato.")
        return
    except Exception:
        st.error("Impossibile leggere detrazioni e deduzioni. Nessun dato modificato.")
        return
    deduzioni = [r for r in deduzioni if not e_contributo(r)]
    st.markdown(f"### 1 · Spese sanitarie · {anno_num}")
    totale_sanitario = manuali + documenti
    detrazione_sanitaria = dd._annuale(totale_sanitario, 1, ALIQUOTA_FOGLIO, True)
    st.metric("Totale unico spese sanitarie inserite", dd._formato(totale_sanitario))
    st.caption(f"Di cui inserite manualmente: {dd._formato(manuali)} · da documenti: "
               f"{dd._formato(documenti)}. La franchigia ipotetica di "
               f"{dd._formato(dd.FRANCHIGIA_FOGLIO)} si applica UNA sola volta alla somma.")
    st.metric("Detrazione sanitaria annua · scenario", dd._formato(detrazione_sanitaria))
    if anomalie:
        st.error("Alcune voci sanitarie hanno più di una rata, un'aliquota diversa dal 19% "
                 "oppure usano impropriamente la descrizione riservata ai documenti. "
                 "Sono escluse dai totali per non applicare formule o franchigie scorrette: "
                 "correggile nella sezione Modifica detrazione, oppure verifica il registro documenti.")
        st.dataframe([{
            "Causale da verificare": r["description"],
            "Importo": dd._formato(D(str(r["original_amount"]))),
            "Rate": r["installment_count"], "%": f"{D(str(r['credit_rate'])) * 100:g}%",
        } for r in anomalie], hide_index=True, width="stretch")
    _carica_documenti(client, anno, crediti, manuali)
    st.divider()
    st.markdown(f"### 2 · Detrazioni attive nell'anno {anno_num}")
    righe = []
    totale = detrazione_sanitaria
    if totale_sanitario > 0:
        righe.append({
            "Causale": "Spese sanitarie · totale unificato", "Importo inserito": dd._formato(totale_sanitario),
            "Rate totali": 1, "N. rata": "—", "Anno prima rata": anno_num,
            "% inserita": "19%", "Detrazione annua (formula)": dd._formato(detrazione_sanitaria),
        })
    for r in altre:
        importo = D(str(r["original_amount"]))
        rate = int(r["installment_count"])
        prima = int(r["first_fiscal_year"])
        numero = dd._numero_rata(anno_num, prima, rate)
        annuo = dd._annuale(importo, rate, D(str(r["credit_rate"])), False)
        totale += annuo
        righe.append({
            "Causale": r["description"], "Importo inserito": dd._formato(importo),
            "Rate totali": rate, "N. rata": f"{numero} / {rate}" if rate > 1 else "—",
            "Anno prima rata": prima, "% inserita": f"{D(str(r['credit_rate'])) * 100:g}%",
            "Detrazione annua (formula)": dd._formato(annuo),
        })
    if righe:
        st.dataframe(righe, hide_index=True, width="stretch")
        st.metric("Totale detrazioni attive · scenario", dd._formato(totale))
    else:
        st.info("Nessuna detrazione attiva registrata.")
    futuri = scaduti = 0
    for r in crediti:
        prima = int(r["first_fiscal_year"])
        if dd._numero_rata(anno_num, prima, int(r["installment_count"])) is None:
            if prima > anno_num:
                futuri += 1
            else:
                scaduti += 1
    if futuri or scaduti:
        st.caption(f"Fuori dalla vista: {futuri} voci future e {scaduti} scadute, conservate nello storico.")
    if anno["status"] == "open":
        st.caption("Per le spese sanitarie manuali usa una rata e l'aliquota dimostrativa del 19%; "
                   "non reinserire le spese già presenti nei documenti.")
        dd._nuova_detrazione(client, anno)
        modificabili = [r for r in crediti if r["description"] != sd.DESCRIZIONE]
        dd._modifica_detrazione(client, modificabili, anno_num)
    else:
        st.info("Anno fiscale chiuso: detrazioni in sola lettura.")
    st.divider()
    st.markdown("### 3 · Deduzioni registrate · input e totale")
    if deduzioni:
        st.dataframe([{
            "Causale": r["description"], "Importo inserito": dd._formato(D(str(r["amount"]))),
            "Data pagamento": r.get("payment_date") or "—",
            "Stato": "Da verificare fiscalmente",
        } for r in deduzioni], hide_index=True, width="stretch")
        totale_deduzioni = sum((D(str(r["amount"])) for r in deduzioni), D("0"))
        st.metric("Totale importi deduzioni registrati · sola somma", dd._formato(totale_deduzioni))
    else:
        st.info("Nessuna deduzione registrata: il fondo pensione dimostrativo non è un versamento.")
    if anno["status"] == "open":
        dd._nuova_deduzione(client, anno)
        dd._modifica_deduzione(client, anno, deduzioni)
    else:
        st.info("Anno fiscale chiuso: deduzioni in sola lettura.")
    st.caption("Prima del collegamento alle imposte verificheremo spettanza, limiti e pagamenti.")
