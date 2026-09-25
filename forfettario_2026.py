"""Prospetti dedicati all'anno 2026 in regime forfettario.

Il modulo riproduce i dati e la logica del file Excel 2026 caricato dall'utente.
Non sostituisce il calcolo dichiarativo del commercialista. In particolare,
lo scenario INPS "-35%" del file viene mantenuto come confronto separato.
"""
from collections import defaultdict
from decimal import Decimal as D, ROUND_HALF_UP

import streamlit as st

from costi_tabella import _proietta
from fatturato import CENT, euro, importo_valido, leggi_fatturato
from imposte_enasarco import calcola_confronto
from mandanti import elenco_mandanti
from registri import anno_aperto, leggi_tutti

PARAMETRI = (
    "forfettario_coeff_redditivita",
    "forfettario_aliquota_sostitutiva",
    "forfettario_limite_ragguagliato",
    "forfettario_limite_uscita_immediata",
    "forfettario_mesi_proiezione",
    "forfettario_contributi_ap",
    "forfettario_riduzione_inps",
    "inps_fisso_foglio",
    "inps_minimale_foglio",
    "inps_aliquota_prima_foglio",
    "inps_soglia_seconda_foglio",
    "inps_aliquota_seconda_foglio",
    "enasarco_tasso_foglio",
    "enasarco_massimale_pluri",
)


def _fmt(v: D) -> str:
    return euro(v.quantize(CENT, rounding=ROUND_HALF_UP))


def _parametri(client, anno_id: str) -> dict[str, dict]:
    righe = leggi_tutti(client, "fiscal_parameters", fiscal_year_id=anno_id)
    return {r["code"]: r for r in righe}


def _valori_parametri(client, anno_id: str) -> dict[str, D] | None:
    presenti = _parametri(client, anno_id)
    if any(c not in presenti for c in PARAMETRI):
        return None
    return {c: D(str(presenti[c]["value"])) for c in PARAMETRI}


def _mesi_compilati(ricavi: list[dict]) -> int:
    return len({int(r["month"]) for r in ricavi})


def calcola_modello_2026(*, fatturato_registrato: D, mesi_compilati: int,
                         costi_annui: D, enasarco: D, p: dict[str, D]) -> dict[str, D]:
    if mesi_compilati <= 0:
        raise ValueError("Serve almeno un mese di fatturato.")
    richiesti = [fatturato_registrato, costi_annui, enasarco, *p.values()]
    if any(not x.is_finite() or x < 0 for x in richiesti):
        raise ValueError("Importi o parametri non validi.")

    mesi_proiezione = p["forfettario_mesi_proiezione"]
    if mesi_proiezione <= 0 or mesi_proiezione > 12 or mesi_proiezione != int(mesi_proiezione):
        raise ValueError("Numero di mesi della proiezione non valido.")

    proiezione_12 = fatturato_registrato / D(mesi_compilati) * D("12")
    fatturato_stimato = fatturato_registrato / D(mesi_compilati) * mesi_proiezione
    redditivita = fatturato_stimato * p["forfettario_coeff_redditivita"]

    minimale = p["inps_minimale_foglio"]
    soglia = p["inps_soglia_seconda_foglio"]
    if soglia < minimale:
        raise ValueError("Soglie INPS non coerenti.")
    if redditivita <= minimale:
        eccedente = D("0")
    elif redditivita <= soglia:
        eccedente = (redditivita - minimale) * p["inps_aliquota_prima_foglio"]
    else:
        eccedente = ((soglia - minimale) * p["inps_aliquota_prima_foglio"]
                     + (redditivita - soglia) * p["inps_aliquota_seconda_foglio"])

    inps_totale = p["inps_fisso_foglio"] + eccedente
    # Replica LETTERALE del foglio: la riduzione del 35% è applicata
    # soltanto alla quota eccedente. Viene mostrata come confronto, non
    # come regola fiscale certificata.
    inps_ridotto_file = (
        p["inps_fisso_foglio"]
        + eccedente * (D("1") - p["forfettario_riduzione_inps"])
    )
    base_sostitutiva_file = max(
        redditivita - p["forfettario_contributi_ap"] - p["inps_fisso_foglio"],
        D("0"),
    )
    imposta = base_sostitutiva_file * p["forfettario_aliquota_sostitutiva"]

    netto = fatturato_stimato - inps_totale - enasarco - costi_annui - imposta
    netto_ridotto_file = (
        fatturato_stimato - inps_ridotto_file - enasarco - costi_annui - imposta
    )
    netto_no_costi = fatturato_stimato - inps_totale - enasarco - imposta
    netto_no_costi_ridotto_file = (
        fatturato_stimato - inps_ridotto_file - enasarco - imposta
    )
    return {
        "fatturato_registrato": fatturato_registrato,
        "proiezione_12_mesi": proiezione_12,
        "fatturato_stimato": fatturato_stimato,
        "redditivita": redditivita,
        "inps_eccedente": eccedente,
        "inps_totale": inps_totale,
        "inps_ridotto_file": inps_ridotto_file,
        "enasarco": enasarco,
        "costi_annui": costi_annui,
        "imposta_sostitutiva": imposta,
        "netto": netto,
        "netto_mese": netto / D("12"),
        "netto_ridotto_file": netto_ridotto_file,
        "netto_ridotto_file_mese": netto_ridotto_file / D("12"),
        "netto_no_costi_mese": netto_no_costi / D("12"),
        "netto_no_costi_ridotto_file_mese": netto_no_costi_ridotto_file / D("12"),
    }


def costi_forfettario(client, anno_id: str) -> tuple[list[dict], D]:
    categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno_id)
    stime = leggi_tutti(client, "annual_cost_estimates", fiscal_year_id=anno_id)
    spese = leggi_tutti(client, "costs", fiscal_year_id=anno_id)

    cat = {r["id"]: r for r in categorie}
    stime_per_cat = {r["category_id"]: r for r in stime}
    spese_per_cat: dict[str, list[dict]] = defaultdict(list)
    for r in spese:
        spese_per_cat[r["category_id"]].append(r)

    righe = []
    totale = D("0")
    for categoria in sorted(categorie, key=lambda r: (r["name"] or "").casefold()):
        cid = categoria["id"]
        elenco = spese_per_cat.get(cid, [])
        registrato = None
        stima = None
        if elenco:
            registrato, stima = _proietta(elenco)
        elif cid in stime_per_cat:
            stima = D(str(stime_per_cat[cid]["estimated_gross_amount"]))
        if stima is None:
            continue
        totale += stima
        righe.append({
            "Voce": categoria["name"],
            "Registrato": _fmt(registrato) if registrato is not None else "—",
            "Stima annua / valore file": _fmt(stima),
        })
    return righe, totale


def mostra_soglie_fatturato(client, anno: dict) -> None:
    try:
        p = _valori_parametri(client, anno["id"])
        ricavi = leggi_fatturato(client, anno["id"])
        if p is None or not ricavi:
            return
        totale = sum((D(str(r["amount"])) for r in ricavi), D("0"))
        mesi = _mesi_compilati(ricavi)
        proiezione = totale / D(mesi) * p["forfettario_mesi_proiezione"]
    except Exception:
        return

    st.markdown("#### Controllo regime forfettario 2026")
    c1, c2, c3 = st.columns(3)
    c1.metric("Fatturato registrato", _fmt(totale))
    c2.metric(
        f"Proiezione file · {int(p['forfettario_mesi_proiezione'])} mesi",
        _fmt(proiezione),
    )
    c3.metric(
        "Margine sul limite 100.000 €",
        _fmt(p["forfettario_limite_uscita_immediata"] - totale),
    )
    st.caption(
        "Il file 2026 usa anche un limite ragguagliato di "
        f"{_fmt(p['forfettario_limite_ragguagliato'])}; rispetto al fatturato "
        f"registrato il margine è {_fmt(p['forfettario_limite_ragguagliato'] - totale)}."
    )


def mostra_costi(client, anno: dict) -> None:
    st.subheader("Costi · regime forfettario 2026")
    st.caption(
        "Questi importi servono a misurare le uscite economiche e il netto di cassa. "
        "Nel modello forfettario il reddito imponibile non viene determinato sottraendo "
        "analiticamente queste spese."
    )
    try:
        righe, totale = costi_forfettario(client, anno["id"])
        stime = leggi_tutti(client, "annual_cost_estimates", fiscal_year_id=anno["id"])
        categorie = {r["id"]: r for r in leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])}
    except Exception:
        st.error("Impossibile leggere i costi 2026.")
        return

    st.dataframe(righe, hide_index=True, width="stretch")
    st.metric("Totale costi annui del modello 2026", _fmt(totale))
    st.caption(
        "Carburante, autostrada e rate auto sono proiettati dai mesi registrati; "
        "le altre voci sono stime annuali importate dal file."
    )

    if anno["status"] != "open" or not stime:
        return
    with st.expander("Modifica una stima annuale importata dal file"):
        opzioni = {
            r["id"]: f"{categorie.get(r['category_id'], {}).get('name', 'Voce')} · {_fmt(D(str(r['estimated_gross_amount'])))}"
            for r in stime
        }
        scelta = st.selectbox(
            "Stima da modificare", list(opzioni),
            format_func=lambda k: opzioni[k],
            key=f"forfettario_stima_{anno['id']}",
        )
        record = next(r for r in stime if r["id"] == scelta)
        with st.form(f"forfettario_stima_form_{scelta}"):
            testo = st.text_input(
                "Nuovo importo annuo (€)",
                value=str(record["estimated_gross_amount"]).replace(".", ","),
            )
            conferma = st.checkbox("Confermo la modifica della stima annuale")
            salva = st.form_submit_button("Salva stima")
        if salva:
            try:
                anno_aperto(client, anno)
                if not conferma:
                    raise ValueError("Conferma la modifica prima di salvare.")
                valore = importo_valido(testo)
                risposta = (
                    client.table("annual_cost_estimates")
                    .update({"estimated_gross_amount": str(valore),
                             "notes": "Valore 2026 modificato manualmente"})
                    .eq("id", record["id"])
                    .eq("fiscal_year_id", anno["id"])
                    .execute()
                )
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Modifica non confermata")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Modifica non confermata: controlla il valore.")
            else:
                st.rerun()


def mostra_conto_economico(client, anno: dict) -> None:
    st.subheader("Conto economico · regime forfettario 2026")
    st.caption(
        "Replica il modello del file Excel 2026: redditività al 62%, imposta sostitutiva "
        "e costi economici separati dal reddito forfettario."
    )
    try:
        p = _valori_parametri(client, anno["id"])
        if p is None:
            st.info("Mancano i parametri importati dal file 2026.")
            return
        ricavi = leggi_fatturato(client, anno["id"])
        if not ricavi:
            st.info("Non ci sono ancora ricavi 2026.")
            return
        fatturato = sum((D(str(r["amount"])) for r in ricavi), D("0"))
        mesi = _mesi_compilati(ricavi)
        mandanti = elenco_mandanti(client)
        _righe, enasarco, mono = calcola_confronto(
            mandanti, ricavi,
            p["enasarco_tasso_foglio"], p["enasarco_massimale_pluri"],
        )
        if mono:
            st.info("Il confronto Enasarco del file richiede rapporti plurimandatari.")
            return
        _costi, totale_costi = costi_forfettario(client, anno["id"])
        valori = calcola_modello_2026(
            fatturato_registrato=fatturato,
            mesi_compilati=mesi,
            costi_annui=totale_costi,
            enasarco=enasarco,
            p=p,
        )
    except ValueError as exc:
        st.warning(str(exc))
        return
    except Exception:
        st.error("Impossibile costruire il conto economico 2026.")
        return

    st.dataframe([
        {"Voce": "Fatturato registrato", "Importo": _fmt(valori["fatturato_registrato"])},
        {"Voce": "Proiezione annualizzata 12 mesi", "Importo": _fmt(valori["proiezione_12_mesi"])},
        {"Voce": f"Fatturato stimato file · {int(p['forfettario_mesi_proiezione'])} mesi",
         "Importo": _fmt(valori["fatturato_stimato"])},
        {"Voce": "Reddito forfettario · coefficiente 62%", "Importo": _fmt(valori["redditivita"])},
        {"Voce": "INPS stimato", "Importo": _fmt(valori["inps_totale"])},
        {"Voce": "Enasarco stimato", "Importo": _fmt(valori["enasarco"])},
        {"Voce": "Costi economici annui", "Importo": _fmt(valori["costi_annui"])},
        {"Voce": "Imposta sostitutiva · modello file", "Importo": _fmt(valori["imposta_sostitutiva"])},
        {"Voce": "Netto annuo stimato", "Importo": _fmt(valori["netto"])},
        {"Voce": "Netto medio / 12", "Importo": _fmt(valori["netto_mese"])},
        {"Voce": "Netto / 12 senza costi", "Importo": _fmt(valori["netto_no_costi_mese"])},
        {"Voce": "Netto annuo · scenario -35% INPS del file",
         "Importo": _fmt(valori["netto_ridotto_file"])},
        {"Voce": "Netto / 12 · scenario -35% INPS del file",
         "Importo": _fmt(valori["netto_ridotto_file_mese"])},
        {"Voce": "Netto / 12 senza costi · scenario -35% del file",
         "Importo": _fmt(valori["netto_no_costi_ridotto_file_mese"])},
    ], hide_index=True, width="stretch")
    st.warning(
        "Lo scenario «-35% INPS» è mantenuto esattamente come nel file 2026 e riduce "
        "solo la quota eccedente. Va considerato un confronto del foglio, non una "
        "certificazione della contribuzione effettivamente dovuta."
    )


def mostra_imposte(client, anno: dict) -> None:
    st.subheader("Imposte · regime forfettario 2026")
    try:
        presenti = _parametri(client, anno["id"])
    except Exception:
        st.error("Impossibile leggere i parametri 2026.")
        return
    descrizioni = [
        ("forfettario_coeff_redditivita", "Coefficiente di redditività", "%"),
        ("forfettario_aliquota_sostitutiva", "Imposta sostitutiva", "%"),
        ("forfettario_limite_ragguagliato", "Limite 85.000 € ragguagliato usato nel file", "€"),
        ("forfettario_limite_uscita_immediata", "Limite uscita immediata", "€"),
        ("forfettario_mesi_proiezione", "Mesi usati nella proiezione del file", "mesi"),
        ("inps_fisso_foglio", "INPS fisso del file", "€"),
        ("inps_minimale_foglio", "Minimale INPS del file", "€"),
        ("inps_aliquota_prima_foglio", "Aliquota INPS prima fascia", "%"),
        ("inps_soglia_seconda_foglio", "Soglia seconda fascia INPS", "€"),
        ("inps_aliquota_seconda_foglio", "Aliquota INPS seconda fascia", "%"),
        ("forfettario_riduzione_inps", "Riduzione INPS nello scenario del file", "%"),
        ("enasarco_tasso_foglio", "Quota personale Enasarco", "%"),
        ("enasarco_massimale_pluri", "Massimale Enasarco plurimandatario", "€"),
    ]
    righe = []
    for codice, nome, tipo in descrizioni:
        record = presenti.get(codice)
        if record is None:
            valore = "—"
        else:
            numero = D(str(record["value"]))
            if tipo == "%":
                valore = f"{numero * 100:g}%"
            elif tipo == "€":
                valore = _fmt(numero)
            else:
                valore = f"{numero:g}"
        righe.append({"Parametro": nome, "Valore importato": valore})
    st.dataframe(righe, hide_index=True, width="stretch")
    st.caption(
        "I parametri sono quelli del file 2026 caricato dall'utente. "
        "Il prospetto serve a replicare e monitorare quel modello."
    )
