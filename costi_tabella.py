"""Un'unica tabella dei costi e moduli di inserimento/modifica sotto la tabella.

Le aliquote iniziali riproducono il foglio di confronto, NON regole fiscali
2027 verificate. Stime annuali e spese mensili restano record distinti.
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

import streamlit as st
from supabase import Client

from auto_rate import quota_deducibile_test
from costi import _calcola, _euro_arrotondato, NOTA_CATEGORIA_TEST

D = Decimal
CENT = D("0.01")
NOTA_MANUALE = "INSERIMENTO MANUALE - parametri fiscali da verificare"
# L'ordine segue il foglio Costi originale. Le voci Auto sono lette da costs,
# non ricopiate in annual_cost_estimates.
VOCI = (
    ("rate_auto", "Auto · rate", "mensile", "0.22", "1", "0.8"),
    ("penale_km", "Penale km", "calcolata", "0", "0", "0"),
    ("carburante", "Carburante", "mensile", "0.22", "1", "0.8"),
    ("autostrada", "Autostrada", "mensile", "0.22", "1", "0.8"),
    ("bollo", "Bollo", "annuale", "0", "0", "0.8"),
    ("assicurazione", "Assicurazione", "annuale", "0", "0", "0.8"),
    ("manutenzione_auto", "Manutenzione auto", "annuale", "0.22", "1", "0.8"),
    ("commercialista", "Commercialista", "annuale", "0.22", "1", "1"),
    ("vitto_alloggio", "Vitto e alloggio", "annuale", "0.22", "1", "0.75"),
    ("pc", "PC", "annuale", "0.22", "1", "1"),
    ("telefono_tablet", "Telefono o tablet", "annuale", "0.22", "1", "0.8"),
)
CONFIG = {voce[0]: voce for voce in VOCI}


def _euro(valore):
    return _euro_arrotondato(valore) if valore is not None else "—"


def _importo(valore):
    try:
        numero = D(str(valore).strip().replace(" ", "").replace("€", "").replace(".", "").replace(",", ".")) if "," in str(valore) else D(str(valore).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Inserisci un importo valido, ad esempio 250,00.") from exc
    if not numero.is_finite() or numero < 0 or numero > D("999999999999.99") or numero != numero.quantize(CENT):
        raise ValueError("L'importo deve essere non negativo, con al massimo due decimali.")
    return numero


def _leggi(client, anno_id):
    from registri import leggi_tutti
    categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno_id)
    stime = leggi_tutti(client, "annual_cost_estimates", fiscal_year_id=anno_id)
    spese = leggi_tutti(client, "costs", fiscal_year_id=anno_id)
    veicoli = leggi_tutti(client, "vehicles")
    impostazioni = leggi_tutti(client, "vehicle_year_settings", fiscal_year_id=anno_id)
    km = leggi_tutti(client, "vehicle_monthly", fiscal_year_id=anno_id)
    return ({c["code"]: c for c in categorie},
            {s["category_id"]: s for s in stime}, spese, veicoli, impostazioni, km)


def _proietta(righe):
    per_veicolo = defaultdict(lambda: defaultdict(lambda: D("0")))
    registrato = D("0")
    for r in righe:
        importo = D(str(r["gross_amount"]))
        registrato += importo
        per_veicolo[r.get("vehicle_id")][int(r["expense_date"][5:7])] += importo
    stima = sum((sum(mesi.values(), D("0")) / len(mesi) * 12
                 for mesi in per_veicolo.values()), D("0")) if righe else None
    return registrato, stima


def _penale(impostazioni, km):
    differenze = []
    for impostazione in impostazioni:
        if impostazione["annual_km_limit"] is None or impostazione["excess_km_penalty"] is None:
            continue
        registrazioni = [r for r in km if r["vehicle_id"] == impostazione["vehicle_id"]]
        if not registrazioni:
            continue
        totale = sum((D(str(r["distance_km"])) for r in registrazioni), D("0"))
        stima = totale / len(registrazioni) * 12
        differenze.append(max(stima - D(str(impostazione["annual_km_limit"])), D("0"))
                          * D(str(impostazione["excess_km_penalty"])))
    return sum(differenze, D("0")) if differenze else None


def _crea_categoria(client, anno_id, codice):
    voce = CONFIG[codice]
    esistente = (client.table("cost_categories").select("id,code,name,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,notes")
                 .eq("fiscal_year_id", anno_id).eq("code", codice).limit(1).execute()).data or []
    if esistente:
        return esistente[0]
    r = client.table("cost_categories").insert({
        "fiscal_year_id": anno_id, "code": codice, "name": voce[1].replace("Auto · ", "").capitalize(),
        "vat_rate": voce[3], "vat_deductible_rate": voce[4],
        "cost_deductible_rate": voce[5], "notes": NOTA_CATEGORIA_TEST,
    }).execute()
    if len(r.data or []) != 1:
        raise RuntimeError("Categoria non confermata")
    return r.data[0]


def _tabella(categorie, stime, spese, impostazioni, km):
    per_cat = defaultdict(list)
    for spesa in spese:
        per_cat[spesa["category_id"]].append(spesa)
    tabella = []
    totali = {k: D("0") for k in ("lordo", "iva", "netto", "deducibile")}
    incompleti = set()
    presenti = 0
    origini = set()
    for codice, nome, tipo, *_ in VOCI:
        cat = categorie.get(codice)
        righe = per_cat[cat["id"]] if cat else []
        stima = stime.get(cat["id"]) if cat else None
        registrato = None
        lordo = iva = netto = deducibile = None
        percentuale = "—"
        origine = "Non inserita"
        if tipo == "calcolata":
            lordo = _penale(impostazioni, km)
            if lordo is not None:
                iva, netto = D("0"), lordo
                deducibile = D("0") if lordo == 0 else None
                origine = "Auto · penale stimata"
                if deducibile is None:
                    incompleti.add(codice)
        elif tipo == "mensile" and righe:
            registrato, lordo = _proietta(righe)
            origine = "Auto · proiezione da mesi"
            origini.update("TEST" if str(r.get("notes") or "").startswith("DATI DI PROVA") else "MANUALE" for r in righe)
            if (cat and all(r["amount_includes_vat"] and
                            all(D(str(r[k])) == D(str(cat[k])) for k in
                                ("vat_rate", "vat_deductible_rate", "cost_deductible_rate")) for r in righe)):
                iva, _detraibile, netto, deducibile = _calcola(lordo, cat, True)
                percentuale = f"{D(str(cat['cost_deductible_rate'])) * 100:g}%"
                if codice == "rate_auto":
                    if (cat.get("notes") == NOTA_CATEGORIA_TEST and
                        all(str(r.get("notes") or "").startswith("DATI DI PROVA") for r in righe)):
                        deducibile = quota_deducibile_test(lordo)
                        percentuale = "63,31%*"
                    else:
                        deducibile = None
                        percentuale = "Da verificare*"
            else:
                incompleti.add(codice)
        elif tipo == "annuale" and stima:
            lordo = D(str(stima["estimated_gross_amount"]))
            origine = "Stima annuale"
            origini.add("TEST" if str(stima.get("notes") or "").startswith("DATI DI PROVA") else "MANUALE")
            if stima["amount_includes_vat"]:
                iva, _detraibile, netto, deducibile = _calcola(lordo, cat, True)
                percentuale = f"{D(str(cat['cost_deductible_rate'])) * 100:g}%"
            else:
                incompleti.add(codice)
        if lordo is not None:
            presenti += 1
            for chiave, importo in (("lordo", lordo), ("iva", iva), ("netto", netto), ("deducibile", deducibile)):
                if importo is None:
                    incompleti.add(codice)
                else:
                    totali[chiave] += importo
        tabella.append({
            "Voce": cat["name"] if cat else nome, "Registrato": _euro(registrato),
            "Totale annuo stimato": _euro(lordo), "IVA scorporata": _euro(iva),
            "Costo netto": _euro(netto), "% deducibilità": percentuale,
            "Da dedurre": _euro(deducibile), "Origine": origine,
        })
    if presenti:
        tabella.append({"Voce": "TOTALE SPESE", "Registrato": "—",
                        "Totale annuo stimato": _euro(totali["lordo"]),
                        "IVA scorporata": "—" if incompleti else _euro(totali["iva"]),
                        "Costo netto": "—" if incompleti else _euro(totali["netto"]),
                        "% deducibilità": "—",
                        "Da dedurre": "—" if incompleti else _euro(totali["deducibile"]),
                        "Origine": "Riepilogo, senza duplicazioni"})
    return tabella, incompleti, origini


def _nuova(client, anno, codice, importo, quando=None, veicolo_id=None, descrizione=""):
    from registri import anno_aperto
    from struttura_calcoli import data_anno
    anno_aperto(client, anno)
    valore = _importo(importo)
    tipo = CONFIG[codice][2]
    if tipo == "mensile" and (not veicolo_id or quando is None):
        raise ValueError("Seleziona un veicolo e una data.")
    if tipo == "mensile":
        data_anno(quando, int(anno["fiscal_year"]))
    categoria = _crea_categoria(client, anno["id"], codice)
    if tipo == "annuale":
        if (client.table("annual_cost_estimates").select("id").eq("fiscal_year_id", anno["id"])
                .eq("category_id", categoria["id"]).limit(1).execute()).data:
            raise ValueError("La stima esiste già: usa Modifica spesa.")
        tabella = "annual_cost_estimates"
        dati = {"fiscal_year_id": anno["id"], "category_id": categoria["id"],
                "estimated_gross_amount": str(valore), "amount_includes_vat": True,
                "notes": NOTA_MANUALE}
    else:
        tabella = "costs"
        dati = {"fiscal_year_id": anno["id"], "category_id": categoria["id"],
                "vehicle_id": veicolo_id, "expense_date": quando.isoformat(),
                "description": descrizione.strip() or CONFIG[codice][1],
                "gross_amount": str(valore), "amount_includes_vat": True,
                "vat_rate": categoria["vat_rate"],
                "vat_deductible_rate": categoria["vat_deductible_rate"],
                "cost_deductible_rate": categoria["cost_deductible_rate"],
                "fiscal_competence_year": int(anno["fiscal_year"]), "notes": NOTA_MANUALE}
    risposta = client.table(tabella).insert(dati).execute()
    if len(risposta.data or []) != 1:
        raise RuntimeError("Inserimento non confermato")


def _modifica(client, anno, categoria, riga, tipo, importo, quando=None, descrizione=""):
    from registri import anno_aperto
    from struttura_calcoli import data_anno
    anno_aperto(client, anno)
    if tipo == "mensile":
        data_anno(quando, int(anno["fiscal_year"]))
    valore = _importo(importo)
    tabella = "annual_cost_estimates" if tipo == "annuale" else "costs"
    dati = {"estimated_gross_amount" if tipo == "annuale" else "gross_amount": str(valore)}
    if tipo == "mensile":
        dati.update({"expense_date": quando.isoformat(), "description": descrizione.strip()})
    risposta = (client.table(tabella).update(dati)
               .eq("id", riga["id"]).eq("fiscal_year_id", anno["id"])
               .eq("category_id", categoria["id"]).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Modifica non confermata")


def _elimina(client, anno, categoria, riga, tipo):
    from registri import anno_aperto
    anno_aperto(client, anno)
    tabella = "annual_cost_estimates" if tipo == "annuale" else "costs"
    risposta = (client.table(tabella).delete().eq("id", riga["id"])
               .eq("fiscal_year_id", anno["id"]).eq("category_id", categoria["id"]).execute())
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata")


def mostra_tabella_costi(client: Client, anno: dict) -> None:
    st.subheader("Costi")
    st.caption("Un'unica tabella: le rate, il carburante e l'autostrada sono letti dai dati Auto. "
               "Le stime annuali NON sono fatture pagate; i valori delle spese mensili sono proiettati su 12 mesi.")
    try:
        categorie, stime, spese, veicoli, impostazioni, km = _leggi(client, anno["id"])
        tabella, incompleti, origini = _tabella(categorie, stime, spese, impostazioni, km)
    except Exception:
        st.error("Impossibile leggere la tabella dei costi. Nessun dato modificato.")
        return
    if "TEST" in origini:
        st.warning("Sono presenti DATI DI PROVA: non rappresentano spese reali.")
    if "MANUALE" in origini:
        st.info("I nuovi importi usano per ora i parametri del foglio originale, non verificati per il 2027.")
    st.dataframe(tabella, hide_index=True, width="stretch")
    if incompleti:
        st.caption("I totali fiscali sono sospesi per voci da verificare: " + ", ".join(sorted(incompleti)) + ".")
    st.caption("* Rate auto: quota deducibile calcolata SOLO sui dati di prova con la formula del foglio. "
               "Il trattamento effettivo del contratto andrà verificato. Assicurazione: premio senza IVA.")
    if anno["status"] != "open":
        st.info("Anno chiuso: costi in sola lettura.")
        return

    st.markdown("**Aggiungi una spesa o una stima**")
    st.caption("Scegli una voce sotto la tabella. Le voci mensili richiedono un veicolo; le altre sono stime annuali.")
    aggiungibili = [v for v in VOCI if v[2] != "calcolata"]
    for inizio in range(0, len(aggiungibili), 4):
        colonne = st.columns(4)
        for colonna, voce in zip(colonne, aggiungibili[inizio:inizio + 4]):
            if colonna.button("＋ " + voce[1], key="costi_aggiungi_" + voce[0], width="stretch"):
                st.session_state["costi_voce_aggiungi"] = voce[0]
    codice = st.session_state.get("costi_voce_aggiungi")
    if codice in CONFIG and CONFIG[codice][2] != "calcolata":
        voce = CONFIG[codice]
        categoria = categorie.get(codice)
        if voce[2] == "annuale" and categoria and categoria["id"] in stime:
            st.info(f"{voce[1]}: è già presente una stima. Utilizza «Modifica una spesa» sotto.")
        elif voce[2] == "mensile" and not veicoli:
            st.warning("Per questa voce crea prima un veicolo nella scheda Auto.")
        else:
            with st.form("costi_form_aggiungi_" + codice):
                st.write("Nuovo inserimento: **" + voce[1] + "**")
                importo = st.text_input("Importo lordo (€), IVA compresa se prevista", placeholder="es. 250,00")
                quando = None
                veicolo_id = None
                descrizione = ""
                if voce[2] == "mensile":
                    veicolo_id = st.selectbox("Veicolo", [v["id"] for v in veicoli],
                                              format_func=lambda vid: next(v["label"] for v in veicoli if v["id"] == vid))
                    quando = st.date_input("Data della spesa", value=date(int(anno["fiscal_year"]), 1, 1),
                                           min_value=date(int(anno["fiscal_year"]), 1, 1),
                                           max_value=date(int(anno["fiscal_year"]), 12, 31))
                    descrizione = st.text_input("Descrizione (facoltativa)")
                st.caption("Parametri fiscali iniziali dal foglio, da verificare. Non è una registrazione IVA né una fattura elettronica.")
                conferma = st.form_submit_button("Salva nuova voce", type="primary")
            if conferma:
                try:
                    _nuova(client, anno, codice, importo, quando, veicolo_id, descrizione)
                except ValueError as exc:
                    st.warning(str(exc))
                except Exception:
                    st.error("Salvataggio non confermato: verifica la tabella prima di riprovare.")
                else:
                    st.session_state.pop("costi_voce_aggiungi", None)
                    st.rerun()

    st.markdown("**Modifica una spesa già inserita**")
    modificabili = []
    for codice_voce, nome, tipo, *_ in VOCI:
        categoria = categorie.get(codice_voce)
        if not categoria or tipo == "calcolata":
            continue
        if tipo == "annuale":
            if categoria["id"] in stime:
                modificabili.append((nome, tipo, categoria, stime[categoria["id"]]))
        else:
            for riga in spese:
                if riga["category_id"] == categoria["id"]:
                    modificabili.append((nome, tipo, categoria, riga))
    if not modificabili:
        st.caption("Non ci sono ancora spese modificabili.")
        return
    opzioni = list(range(len(modificabili)))
    scelta = st.selectbox("Seleziona la voce da modificare", opzioni,
                          format_func=lambda i: (
                              modificabili[i][0] + " · " +
                              (modificabili[i][3]["expense_date"] + " · " if modificabili[i][1] == "mensile" else "stima annua · ") +
                              _euro(D(str(modificabili[i][3]["gross_amount"] if modificabili[i][1] == "mensile" else modificabili[i][3]["estimated_gross_amount"])))
                          ), key="costi_modifica_selezione")
    nome, tipo, categoria, riga = modificabili[scelta]
    valore = D(str(riga["estimated_gross_amount"] if tipo == "annuale" else riga["gross_amount"]))
    with st.form("costi_form_modifica_" + riga["id"]):
        nuovo_importo = st.text_input("Nuovo importo lordo (€)", value=f"{valore:.2f}".replace(".", ","))
        nuova_data = None
        descrizione = ""
        if tipo == "mensile":
            nuova_data = st.date_input("Data", value=date.fromisoformat(riga["expense_date"]),
                                       min_value=date(int(anno["fiscal_year"]), 1, 1),
                                       max_value=date(int(anno["fiscal_year"]), 12, 31))
            descrizione = st.text_input("Descrizione", value=riga.get("description") or "")
        st.caption("La modifica conserva l'origine TEST di un dato di prova; non modifica aliquote o altri record.")
        salva = st.form_submit_button("Salva modifica", type="primary")
    if salva:
        try:
            _modifica(client, anno, categoria, riga, tipo, nuovo_importo, nuova_data, descrizione)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Modifica non confermata: controlla la tabella prima di riprovare.")
        else:
            st.rerun()
    with st.expander("Elimina la voce selezionata"):
        eliminare = st.checkbox("Confermo l'eliminazione definitiva di questa singola voce", key="costi_conferma_elimina_" + riga["id"])
        if st.button("Elimina voce", key="costi_elimina_" + riga["id"], disabled=not eliminare):
            try:
                _elimina(client, anno, categoria, riga, tipo)
            except Exception:
                st.error("Eliminazione non confermata: controlla la tabella prima di riprovare.")
            else:
                st.rerun()
