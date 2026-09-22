"""Detrazioni e deduzioni: registrazioni manuali distinte da esempi matematici.

Le rate scadute scompaiono dalla vista annuale senza eliminare lo storico.
I valori non sono ancora collegati alle imposte definitive.
"""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import euro

D = Decimal
CENT = D("0.01")
FRANCHIGIA_FOGLIO = D("129.11")
# Marcatori legacy dei record sanitari: non modificarli.
MARCATORE_SANITARIE = "TIPO_SANITARIE_FOGLIO; PARAMETRI FISCALI DA VERIFICARE"
MARCATORE_ORDINARIE = "PARAMETRI FISCALI DA VERIFICARE"
NOTA_DEDUZIONE = "DA VERIFICARE: registrazione manuale, non deduzione fiscale approvata"
PROVE = (
    ("Spese sanitarie", "517", 1, None, "0.19", True),
    ("Mutuo", "527", 1, None, "0.19", False),
    ("Donazioni", "530", 1, None, "0.30", False),
    ("Casa", "5321", 10, 10, "0.50", False),
    ("Casa", "25815", 10, 9, "0.50", False),
    ("Casa", "24", 10, 8, "0.50", False),
    ("Mobili", "7835", 10, 7, "0.50", False),
    ("Risparmio energetico", "59", 10, 7, "0.50", False),
    ("Risparmio energetico", "1298", 10, 5, "1.10", False),
    ("Rec. patrimonio edilizio", "84", 10, 7, "0.50", False),
    ("Rec. patrimonio edilizio", "124", 10, 5, "0.50", False),
    ("Rec. patrimonio edilizio", "615", 10, 4, "0.50", False),
    ("Infissi", "8580", 10, 4, "0.50", False),
    ("Condominio", "733", 10, 3, "0.50", False),
    ("Condominio", "128", 10, 3, "0.50", False),
)


def _denaro(testo: str) -> D:
    valore = str(testo).strip().replace("€", "").replace(" ", "")
    if "," in valore:
        valore = valore.replace(".", "").replace(",", ".")
    try:
        numero = D(valore)
    except InvalidOperation as exc:
        raise ValueError("Inserisci un importo valido, ad esempio 530,00.") from exc
    if not numero.is_finite() or numero < 0 or numero > D("999999999999.99") or numero != numero.quantize(CENT):
        raise ValueError("L'importo deve essere positivo o zero, con massimo due decimali.")
    return numero


def _aliquota(testo: str) -> D:
    numero = _denaro(testo) / D("100")
    if numero > 2:
        raise ValueError("La percentuale di confronto deve essere compresa fra 0% e 200%.")
    return numero


def _annuale(importo: D, rate: int, aliquota: D, sanitarie: bool) -> D:
    """Spese sanitarie: max(0,importo-franchigia)/rate*aliquota."""
    if rate < 1 or rate > 30 or aliquota < 0 or aliquota > 2:
        raise ValueError("Numero rate o percentuale non valido.")
    base = max(D("0"), importo - FRANCHIGIA_FOGLIO) if sanitarie else importo
    return base / D(rate) * aliquota


def _formato(valore: D) -> str:
    return euro(valore.quantize(CENT, rounding=ROUND_HALF_UP))


def _data(testo: str, anno: int) -> str:
    try:
        giorno = date.fromisoformat(testo.strip())
    except ValueError as exc:
        raise ValueError("Inserisci una data valida nel formato AAAA-MM-GG.") from exc
    if giorno.year != anno:
        raise ValueError(f"Per la scheda {anno} inserisci un pagamento avvenuto nel {anno}.")
    return giorno.isoformat()


def _leggi(client: Client, anno: dict) -> tuple[list[dict], list[dict]]:
    from registri import leggi_tutti
    deduzioni = leggi_tutti(client, "tax_deductions", fiscal_year_id=anno["id"])
    detrazioni = leggi_tutti(client, "tax_credits")
    return detrazioni, deduzioni


def _validazione_voce(descrizione: str, importo: str) -> tuple[str, D]:
    nome = " ".join(descrizione.split())
    if not nome or len(nome) > 200:
        raise ValueError("Inserisci una causale di massimo 200 caratteri.")
    return nome, _denaro(importo)


def _numero_rata(anno: int, primo_anno: int, numero_rate: int) -> int | None:
    if numero_rate < 1 or numero_rate > 30:
        raise ValueError("Numero totale delle rate non valido.")
    corrente = anno - primo_anno + 1
    return corrente if 1 <= corrente <= numero_rate else None


def _anteprima_foglio() -> None:
    """Prospetto matematico dimostrativo, lasciato per compatibilita'."""
    st.markdown("### Esempi dimostrativi · sola lettura")
    st.caption("Importi ipotetici, non registrati nel database né verificati fiscalmente.")
    righe = []
    importi = D("0")
    totale = D("0")
    for nome, testo, rate, numero, tasso, sanitaria in PROVE:
        valore = D(testo)
        annuo = _annuale(valore, rate, D(tasso), sanitaria)
        importi += valore
        totale += annuo
        righe.append({
            "Causale": nome, "Importo ipotetico": _formato(valore),
            "Rate annuali": rate,
            "N. rata di prova": str(numero) if numero is not None else "—",
            "% ipotizzata": f"{D(tasso) * 100:g}%",
            "Detrazione annua ipotetica": _formato(annuo),
        })
    st.dataframe(righe, hide_index=True, width="stretch")
    st.caption("Spese sanitarie: max(0; importo − franchigia) / rate × aliquota. "
               "Altre voci: importo / rate × aliquota. Il numero della rata determina "
               "gli anni in cui una voce è visualizzata.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Importi di prova", _formato(importi))
    c2.metric("Detrazioni di prova", _formato(totale))
    c3.metric("Fondo pensione dimostrativo", _formato(D("5300")))
    if importi == D("52190") and totale.quantize(CENT, rounding=ROUND_HALF_UP) == D("2941.51"):
        st.success("Verifica numerica del caso dimostrativo riuscita.")
    else:
        st.error("Il caso dimostrativo presenta differenze: non usare i risultati.")


def _nuova_detrazione(client: Client, anno: dict) -> None:
    anno_fiscale = int(anno["fiscal_year"])
    with st.expander("➕ Aggiungi una nuova riga di detrazione", expanded=True):
        st.caption("Per una nuova detrazione indica rata 1. Se il piano è già iniziato, "
                   f"indica la rata spettante nel {anno_fiscale}: l'anno iniziale verrà ricavato automaticamente. "
                   "Il numero avanzerà di uno a ogni anno fiscale, senza modifiche manuali.")
        with st.form("credit_create", clear_on_submit=True):
            descrizione = st.text_input("Causale")
            importo = st.text_input("Importo originario (€)", placeholder="es. 527,00")
            rate = st.number_input("Numero complessivo di rate annuali", min_value=1, max_value=30, value=1, step=1)
            corrente = st.number_input(f"Numero della rata nel {anno_fiscale} (1 = prima rata)",
                                       min_value=1, max_value=30, value=1, step=1)
            percentuale = st.text_input("Percentuale detrazione (%)", placeholder="es. 19 oppure 110")
            sanitaria = st.checkbox("Spese sanitarie: applica la franchigia di scenario (129,11 €)")
            salva = st.form_submit_button("Salva nuova riga di detrazione")
        if salva:
            try:
                if int(corrente) > int(rate):
                    raise ValueError("La rata corrente non può superare il numero complessivo di rate.")
                prima = anno_fiscale - int(corrente) + 1
                if not 2000 <= prima <= 2100:
                    raise ValueError("Anno di prima rata fuori dall'intervallo gestito (2000–2100).")
                nome, valore = _validazione_voce(descrizione, importo)
                aliquota = _aliquota(percentuale)
                _annuale(valore, int(rate), aliquota, sanitaria)
                risposta = client.table("tax_credits").insert({
                    "description": nome, "original_amount": str(valore),
                    "credit_rate": str(aliquota), "installment_count": int(rate),
                    "first_fiscal_year": prima,
                    "notes": MARCATORE_SANITARIE if sanitaria else MARCATORE_ORDINARIE,
                }).execute()
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Inserimento non confermato")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Salvataggio non confermato: controlla la tabella prima di riprovare.")
            else:
                st.rerun()


def _modifica_detrazione(client: Client, crediti: list[dict], anno_fiscale: int) -> None:
    if not crediti:
        return
    with st.expander("Modifica o elimina una detrazione · anche scaduta"):
        opzioni = {r["id"]: r for r in crediti}
        scelto = st.selectbox("Detrazione", list(opzioni),
                             format_func=lambda k: f"{opzioni[k]['description']} · prima rata {opzioni[k]['first_fiscal_year']}",
                             key="credit_choice")
        r = opzioni[scelto]
        numero = _numero_rata(anno_fiscale, int(r["first_fiscal_year"]), int(r["installment_count"]))
        st.caption(f"Rata per il {anno_fiscale}: {numero}/{r['installment_count']}" if numero is not None
                   else "La voce non è attiva nell'anno selezionato. Lo storico resta disponibile.")
        with st.form(f"credit_edit_{scelto}"):
            nome = st.text_input("Causale", value=r["description"])
            importo = st.text_input("Importo originario (€)", value=str(r["original_amount"]).replace(".", ","))
            rate = st.number_input("Numero complessivo di rate annuali", min_value=1, max_value=30,
                                   value=int(r["installment_count"]), step=1)
            prima = st.number_input("Anno della prima rata (il numero corrente viene calcolato)",
                                    min_value=2000, max_value=2100,
                                    value=int(r["first_fiscal_year"]), step=1)
            percentuale = st.text_input("Percentuale (%)", value=str(D(str(r["credit_rate"])) * 100).replace(".", ","))
            sanitaria = st.checkbox("Usa franchigia sanitaria di scenario",
                                    value=str(r.get("notes") or "").startswith("TIPO_SANITARIE_FOGLIO"))
            cancella = st.checkbox("Elimina definitivamente questa registrazione")
            salva = st.form_submit_button("Conferma operazione")
        if salva:
            try:
                if cancella:
                    risposta = client.table("tax_credits").delete().eq("id", scelto).execute()
                else:
                    descrizione, valore = _validazione_voce(nome, importo)
                    aliquota = _aliquota(percentuale)
                    _annuale(valore, int(rate), aliquota, sanitaria)
                    risposta = client.table("tax_credits").update({
                        "description": descrizione, "original_amount": str(valore),
                        "credit_rate": str(aliquota), "installment_count": int(rate),
                        "first_fiscal_year": int(prima),
                        "notes": MARCATORE_SANITARIE if sanitaria else MARCATORE_ORDINARIE,
                    }).eq("id", scelto).execute()
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Modifica non confermata")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Operazione non confermata: ricontrolla la tabella prima di riprovare.")
            else:
                st.rerun()


def _nuova_deduzione(client: Client, anno: dict) -> None:
    with st.expander("Aggiungi una deduzione · dati manuali"):
        with st.form("deduction_create", clear_on_submit=True):
            nome = st.text_input("Causale (es. Fondo pensione)")
            importo = st.text_input("Importo (€)", placeholder="es. 5300,00")
            data = st.text_input("Data del pagamento (AAAA-MM-GG)", placeholder=f"{anno['fiscal_year']}-MM-GG")
            salva = st.form_submit_button("Aggiungi deduzione")
        if salva:
            try:
                descrizione, valore = _validazione_voce(nome, importo)
                pagamento = _data(data, int(anno["fiscal_year"]))
                risposta = client.table("tax_deductions").insert({
                    "fiscal_year_id": anno["id"], "description": descrizione,
                    "amount": str(valore), "payment_date": pagamento,
                    "notes": NOTA_DEDUZIONE,
                }).execute()
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Inserimento non confermato")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Salvataggio non confermato: controlla la tabella prima di riprovare.")
            else:
                st.rerun()


def _modifica_deduzione(client: Client, anno: dict, deduzioni: list[dict]) -> None:
    if not deduzioni:
        return
    with st.expander("Modifica o elimina una deduzione"):
        opzioni = {r["id"]: r for r in deduzioni}
        scelto = st.selectbox("Deduzione", list(opzioni), format_func=lambda k: opzioni[k]["description"],
                             key="deduction_choice")
        r = opzioni[scelto]
        with st.form(f"deduction_edit_{scelto}"):
            nome = st.text_input("Causale", value=r["description"])
            importo = st.text_input("Importo (€)", value=str(r["amount"]).replace(".", ","))
            data = st.text_input("Data pagamento (AAAA-MM-GG)", value=str(r.get("payment_date") or ""))
            cancella = st.checkbox("Elimina questa registrazione")
            salva = st.form_submit_button("Elimina registrazione" if cancella else "Salva modifiche")
        if salva:
            try:
                if cancella:
                    risposta = (client.table("tax_deductions").delete().eq("id", scelto)
                                .eq("fiscal_year_id", anno["id"]).execute())
                else:
                    descrizione, valore = _validazione_voce(nome, importo)
                    pagamento = _data(data, int(anno["fiscal_year"]))
                    risposta = (client.table("tax_deductions").update({
                        "description": descrizione, "amount": str(valore), "payment_date": pagamento,
                        "notes": NOTA_DEDUZIONE,
                    }).eq("id", scelto).eq("fiscal_year_id", anno["id"]).execute())
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Modifica non confermata")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Operazione non confermata: ricontrolla la tabella prima di riprovare.")
            else:
                st.rerun()


def mostra_detrazioni_deduzioni(client: Client, anno: dict) -> None:
    """Vista storica di compatibilita'; l'app usa sanitarie_unificate."""
    st.subheader("Detrazioni e deduzioni")
    st.warning("Aliquote, franchigie e ammissibilità fiscale sono scenari non verificati per il 2027.")
    anno_fiscale = int(anno["fiscal_year"])
    st.info("Le rate pluriennali avanzano di uno per ogni anno fiscale e scompaiono dalla "
            "vista annuale dopo l'ultima rata; lo storico resta nel database.")
    try:
        crediti, deduzioni = _leggi(client, anno)
    except Exception:
        st.error("Impossibile leggere detrazioni e deduzioni. Nessun dato modificato.")
        return
    st.markdown(f"### 1 · Detrazioni attive nell'anno {anno_fiscale}")
    righe_crediti = []
    totale_crediti = D("0")
    future = scadute = 0
    for r in crediti:
        importo = D(str(r["original_amount"]))
        rate = int(r["installment_count"])
        prima = int(r["first_fiscal_year"])
        numero = _numero_rata(anno_fiscale, prima, rate)
        if numero is None:
            if prima > anno_fiscale:
                future += 1
            else:
                scadute += 1
            continue
        sanitaria = str(r.get("notes") or "").startswith("TIPO_SANITARIE_FOGLIO")
        annuo = _annuale(importo, rate, D(str(r["credit_rate"])), sanitaria)
        totale_crediti += annuo
        righe_crediti.append({
            "Causale": r["description"], "Importo inserito": _formato(importo),
            "Rate totali": rate, "N. rata": f"{numero} / {rate}" if rate > 1 else "—",
            "Anno prima rata": prima, "% inserita": f"{D(str(r['credit_rate'])) * 100:g}%",
            "Detrazione annua (formula)": _formato(annuo),
        })
    if righe_crediti:
        st.dataframe(righe_crediti, hide_index=True, width="stretch")
        st.metric("Totale detrazioni attive · scenario", _formato(totale_crediti))
    else:
        st.info("Nessuna detrazione attiva registrata.")
    if future or scadute:
        st.caption(f"Fuori dalla tabella dell'anno: {future} future e {scadute} scadute. "
                   "Restano nello storico.")
    if anno["status"] == "open":
        _nuova_detrazione(client, anno)
        _modifica_detrazione(client, crediti, anno_fiscale)
    else:
        st.info("Anno fiscale chiuso: detrazioni in sola lettura.")
    st.divider()
    st.markdown("### 2 · Deduzioni registrate · input e somma")
    if deduzioni:
        st.dataframe([{
            "Causale": r["description"], "Importo inserito": _formato(D(str(r["amount"]))),
            "Data pagamento": r.get("payment_date") or "—",
            "Stato": "Da verificare fiscalmente",
        } for r in deduzioni], hide_index=True, width="stretch")
        totale_deduzioni = sum((D(str(r["amount"])) for r in deduzioni), D("0"))
        st.metric("Totale deduzioni registrate · sola somma", _formato(totale_deduzioni))
    else:
        st.info("Nessuna deduzione registrata; i valori dimostrativi non sono pagamenti.")
    if anno["status"] == "open":
        _nuova_deduzione(client, anno)
        _modifica_deduzione(client, anno, deduzioni)
    else:
        st.info("Anno fiscale chiuso: deduzioni in sola lettura.")
