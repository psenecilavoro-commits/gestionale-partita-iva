"""Detrazioni e deduzioni: ingressi manuali separati dalle formule del foglio.

Anteprima del foglio SOLO in memoria, mai importata in Supabase.
Registrazioni manuali in tax_credits/tax_deductions: non validate fiscalmente
ne' collegate automaticamente a imposte, netto o versamenti.
"""
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import streamlit as st
from supabase import Client

from fatturato import euro

D = Decimal
CENT = D("0.01")
FRANCHIGIA_FOGLIO = D("129.11")
MARCATORE_SANITARIE = "TIPO_SANITARIE_FOGLIO; PARAMETRI FISCALI DA VERIFICARE"
MARCATORE_ORDINARIE = "PARAMETRI FISCALI DA VERIFICARE"
NOTA_DEDUZIONE = "DA VERIFICARE: registrazione manuale, non deduzione fiscale approvata"

# Trascrizione delle celle B/C/E bianche, F grigie (A3:F17).
# Il numero della rata nella colonna D e' informativo: NON entra nelle formule F.
PROVE = (
    ("Spese sanitarie", "517", 1, "0.19", True),
    ("Mutuo", "527", 1, "0.19", False),
    ("Donazioni", "530", 1, "0.30", False),
    ("Casa", "5321", 10, "0.50", False),
    ("Casa", "25815", 10, "0.50", False),
    ("Casa", "24", 10, "0.50", False),
    ("Mobili", "7835", 10, "0.50", False),
    ("Risparmio energetico", "59", 10, "0.50", False),
    ("Risparmio energetico", "1298", 10, "1.10", False),
    ("Rec. patrimonio edilizio", "84", 10, "0.50", False),
    ("Rec. patrimonio edilizio", "124", 10, "0.50", False),
    ("Rec. patrimonio edilizio", "615", 10, "0.50", False),
    ("Infissi", "8580", 10, "0.50", False),
    ("Condominio", "733", 10, "0.50", False),
    ("Condominio", "128", 10, "0.50", False),
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
    numero = _denaro(testo) / 100
    if numero > 2:
        raise ValueError("La percentuale di confronto deve essere compresa fra 0% e 200%.")
    return numero


def _annuale(importo: D, rate: int, aliquota: D, sanitarie: bool) -> D:
    """F = MAX(0;B-129,11)/C*E per sanitarie, altrimenti B/C*E."""
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
    deduzioni = (client.table("tax_deductions")
                 .select("id,description,amount,payment_date,notes")
                 .eq("fiscal_year_id", anno["id"]).order("description").execute()).data or []
    # I crediti sono associati a first_fiscal_year, non a fiscal_year_id.
    detrazioni = (client.table("tax_credits")
                  .select("id,description,original_amount,credit_rate,installment_count,first_fiscal_year,notes")
                  .order("description").execute()).data or []
    return detrazioni, deduzioni


def _validazione_voce(descrizione: str, importo: str) -> tuple[str, D]:
    nome = " ".join(descrizione.split())
    if not nome or len(nome) > 200:
        raise ValueError("Inserisci una causale di massimo 200 caratteri.")
    return nome, _denaro(importo)


def _anteprima_foglio() -> None:
    st.markdown("### 1 · Confronto con il foglio originale · sola lettura")
    st.caption("Le celle bianche del foglio sono trascritte come esempi; le colonne calcolate non sono modificabili. "
               "Questi dati NON sono caricati in Supabase e non rappresentano detrazioni approvate per il 2027.")
    righe = []
    importi = D("0")
    totale = D("0")
    for nome, testo, rate, tasso, sanitaria in PROVE:
        valore = D(testo)
        annuo = _annuale(valore, rate, D(tasso), sanitaria)
        importi += valore
        totale += annuo
        righe.append({"Causale": nome, "Importo (input)": _formato(valore),
                      "Rate annue (input)": rate, "% (input)": f"{D(tasso) * 100:g}%",
                      "Detrazione annua (formula)": _formato(annuo)})
    st.dataframe(righe, hide_index=True, use_container_width=True)
    st.caption("Spese sanitarie: F3 = MAX(0; B3 − 129,11)/C3 × E3. "
               "Altre righe: F = B/C × E. Il valore della colonna «N. rata» non entra in queste formule.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Importi di prova · B19", _formato(importi))
    c2.metric("Detrazioni di prova · F19", _formato(totale))
    c3.metric("Fondo pensione di prova · I3", _formato(D("5300")))
    if importi == D("52190") and totale.quantize(CENT, rounding=ROUND_HALF_UP) == D("2941.51"):
        st.success("Le formule di prova riproducono i totali del foglio: 52.190,00 € e 2.941,51 €.")
    else:
        st.error("Il confronto non coincide: non usare i risultati.")


def _nuova_detrazione(client: Client, anno: dict) -> None:
    with st.expander("Aggiungi una detrazione · dati manuali"):
        with st.form("credit_create", clear_on_submit=True):
            descrizione = st.text_input("Causale")
            importo = st.text_input("Importo originario (€)", placeholder="es. 527,00")
            rate = st.number_input("Numero rate annuali", min_value=1, max_value=30, value=1, step=1)
            prima = st.number_input("Anno della prima rata (da indicare, non dedotto dal foglio)",
                                    min_value=2000, max_value=2100, value=int(anno["fiscal_year"]), step=1)
            percentuale = st.text_input("Percentuale detrazione (%)", placeholder="es. 19 oppure 110")
            sanitaria = st.checkbox("Spese sanitarie: applica solo la franchigia di confronto del foglio (129,11 €)")
            salva = st.form_submit_button("Aggiungi detrazione")
        if salva:
            try:
                nome, valore = _validazione_voce(descrizione, importo)
                aliquota = _aliquota(percentuale)
                _annuale(valore, int(rate), aliquota, sanitaria)
                risposta = client.table("tax_credits").insert({
                    "description": nome, "original_amount": str(valore),
                    "credit_rate": str(aliquota), "installment_count": int(rate),
                    "first_fiscal_year": int(prima),
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


def _modifica_detrazione(client: Client, crediti: list[dict]) -> None:
    if not crediti:
        return
    with st.expander("Modifica o elimina una detrazione"):
        opzioni = {r["id"]: r for r in crediti}
        scelto = st.selectbox("Detrazione", list(opzioni),
                             format_func=lambda k: f"{opzioni[k]['description']} · prima rata {opzioni[k]['first_fiscal_year']}",
                             key="credit_choice")
        r = opzioni[scelto]
        with st.form(f"credit_edit_{scelto}"):
            nome = st.text_input("Causale", value=r["description"])
            importo = st.text_input("Importo originario (€)", value=str(r["original_amount"]).replace(".", ","))
            rate = st.number_input("Numero rate annuali", min_value=1, max_value=30,
                                   value=int(r["installment_count"]), step=1)
            prima = st.number_input("Anno della prima rata", min_value=2000, max_value=2100,
                                    value=int(r["first_fiscal_year"]), step=1)
            percentuale = st.text_input("Percentuale (%)", value=str(D(str(r["credit_rate"])) * 100).replace(".", ","))
            sanitaria = st.checkbox("Usa franchigia sanitaria del foglio", value=str(r.get("notes") or "").startswith("TIPO_SANITARIE_FOGLIO"))
            cancella = st.checkbox("Elimina questa registrazione")
            salva = st.form_submit_button("Elimina registrazione" if cancella else "Salva modifiche")
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
    st.subheader("Detrazioni e deduzioni")
    st.warning("Le formule riproducono SOLO il foglio originale: percentuali, franchigia e ammissibilità "
               "fiscale non sono ancora verificate per il 2027. Nessun dato qui cambia imposte o netto.")
    _anteprima_foglio()
    try:
        crediti, deduzioni = _leggi(client, anno)
    except Exception:
        st.error("Impossibile leggere detrazioni e deduzioni. Nessun dato modificato.")
        return

    st.divider()
    st.markdown("### 2 · Detrazioni registrate · input bianchi, risultato calcolato")
    anno_fiscale = int(anno["fiscal_year"])
    righe_crediti = []
    totale_crediti = D("0")
    for r in crediti:
        importo = D(str(r["original_amount"]))
        rate = int(r["installment_count"])
        prima = int(r["first_fiscal_year"])
        attiva = prima <= anno_fiscale < prima + rate
        sanitaria = str(r.get("notes") or "").startswith("TIPO_SANITARIE_FOGLIO")
        annuo = _annuale(importo, rate, D(str(r["credit_rate"])), sanitaria) if attiva else D("0")
        totale_crediti += annuo
        righe_crediti.append({
            "Causale": r["description"], "Importo inserito": _formato(importo),
            "Rate inserite": rate, "Anno prima rata": prima,
            "N. rata (calcolata)": anno_fiscale - prima + 1 if attiva else "Fuori periodo",
            "% inserita": f"{D(str(r['credit_rate'])) * 100:g}%",
            "Detrazione annua (formula)": _formato(annuo) if attiva else "—",
        })
    if righe_crediti:
        st.dataframe(righe_crediti, hide_index=True, use_container_width=True)
        st.metric("Totale detrazioni di confronto registrate", _formato(totale_crediti))
    else:
        st.info("Nessuna detrazione registrata: l'anteprima del foglio NON viene inserita automaticamente.")
    if anno["status"] == "open":
        _nuova_detrazione(client, anno)
        _modifica_detrazione(client, crediti)

    st.divider()
    st.markdown("### 3 · Deduzioni registrate · input bianchi, somma calcolata")
    if deduzioni:
        st.dataframe([{
            "Causale": r["description"], "Importo inserito": _formato(D(str(r["amount"]))),
            "Data pagamento": r.get("payment_date") or "—",
            "Stato": "Da verificare fiscalmente",
        } for r in deduzioni], hide_index=True, use_container_width=True)
        totale_deduzioni = sum((D(str(r["amount"])) for r in deduzioni), D("0"))
        st.metric("Totale importi deduzioni registrati · sola somma", _formato(totale_deduzioni))
    else:
        st.info("Nessuna deduzione registrata: i 5.300 € del fondo pensione del foglio restano SOLO un esempio.")
    if anno["status"] == "open":
        _nuova_deduzione(client, anno)
        _modifica_deduzione(client, anno, deduzioni)
    else:
        st.info("Anno fiscale chiuso: registrazioni in sola lettura.")
    st.caption("Le detrazioni riducono in potenza l'imposta, le deduzioni l'imponibile: "
               "qui mostriamo soltanto le formule del foglio e le cifre registrate. "
               "Prima di usarle nei risultati fiscali verificheremo spettanza, limiti e pagamenti.")