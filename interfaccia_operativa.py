"""Schermate operative: nessun pulsante di caricamento o scenario dimostrativo.

Le funzioni matematiche e i marcatori storici restano nei moduli tecnici per
compatibilità e per individuare con precisione i record demo nel database.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

import streamlit as st

from auto import NOTA_VEICOLO_TEST, _chilometri, _veicoli, auto_unica
from auto_limiti import _leggi_impostazioni
from auto_riepilogo import costruisci_tabella_auto, riepilogo_limite_penale
from fatturato import (MESI, CENT, euro, importo_valido, leggi_fatturato,
                       riepilogo, salva_fatturato, elimina_fatturato)
from imposte_parametri import GRUPPI, _leggi as leggi_parametri, _numero, _formato, _modifica
from registri import leggi_tutti, anno_aperto

D = Decimal


def mostra_fatturato(client, anno: dict, mandanti: list[dict]) -> None:
    """Gestione dei soli importi immessi dall'utente; nessun generatore demo."""
    st.divider()
    st.subheader(f"Fatturato registrato · {anno['fiscal_year']}")
    st.caption("Importi fatturati IVA esclusa. La stima annua usa soltanto i mesi compilati; un mese non compilato non equivale a zero.")
    if not mandanti:
        st.info("Aggiungi prima una mandante nella sezione Mandanti.")
        return
    try:
        righe = leggi_fatturato(client, anno["id"])
        risultati, maturato, proiezione = riepilogo(mandanti, righe)
    except ValueError as exc:
        st.error(f"Controlla i dati del fatturato: {exc}")
        return
    except Exception:
        st.error("Impossibile leggere il fatturato. Nessun dato modificato.")
        return
    if any(str(r.get("notes") or "").startswith("DATI DI PROVA") for r in righe):
        st.warning("Sono ancora presenti ricavi dimostrativi nel database: non considerarli ricavi effettivi. Esegui la pulizia controllata prima di usare il gestionale.")
    c1, c2 = st.columns(2)
    c1.metric("Fatturato registrato", euro(maturato))
    c2.metric("Stima a fine anno", euro(proiezione.quantize(CENT, rounding=ROUND_HALF_UP)) if proiezione is not None else "—")
    indice = {(r["principal_id"], int(r["month"])): r for r in righe}
    vista = []
    for mese in range(1, 13):
        riga = {"Mese": MESI[mese - 1]}
        importi = []
        for mandante in mandanti:
            presente = indice.get((mandante["id"], mese))
            valore = D(str(presente["amount"])) if presente else None
            riga[mandante["name"]] = euro(valore) if valore is not None else "—"
            if valore is not None:
                importi.append(valore)
        riga["Totale mese"] = euro(sum(importi, D("0"))) if importi else "—"
        vista.append(riga)
    st.dataframe(vista, hide_index=True, width="stretch")
    st.markdown("**Riepilogo per mandante**")
    st.dataframe([{
        "Mandante": r["nome"], "Mesi compilati": r["mesi"],
        "Fatturato": euro(r["totale"]),
        "Media mesi compilati": euro(r["media"].quantize(CENT, rounding=ROUND_HALF_UP)) if r["media"] is not None else "—",
        "Stima annua": euro(r["stima"].quantize(CENT, rounding=ROUND_HALF_UP)) if r["stima"] is not None else "—",
    } for r in risultati], hide_index=True, width="stretch")
    if anno["status"] != "open":
        st.info("Anno chiuso: fatturato in sola lettura.")
        return
    st.markdown("**Inserisci o modifica un mese**")
    nomi = {m["name"]: m["id"] for m in mandanti}
    nome = st.selectbox("Mandante", list(nomi), key="fatturato_mandante")
    mese_nome = st.selectbox("Mese", MESI, key="fatturato_mese")
    mese = MESI.index(mese_nome) + 1
    presente = indice.get((nomi[nome], mese))
    if presente:
        st.caption("Il mese è già registrato: salvando ne sostituisci l'importo.")
    with st.form("salva_fatturato"):
        testo = st.text_input("Importo fatturato (IVA esclusa)",
                              value=str(presente["amount"]).replace(".", ",") if presente else "",
                              help="Inserisci 0 solo se il fatturato del mese è realmente zero.")
        salva = st.form_submit_button("Salva importo", type="primary")
    if salva:
        try:
            anno_aperto(client, anno)
            salva_fatturato(client, anno["id"], nomi[nome], mese, importo_valido(testo), presente)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Salvataggio non confermato: verifica la tabella prima di riprovare.")
        else:
            st.rerun()
    if righe:
        with st.expander("Elimina un importo registrato"):
            nomi_id = {m["id"]: m["name"] for m in mandanti}
            opzioni = {r["id"]: r for r in righe}
            selezione = st.selectbox("Importo da eliminare", list(opzioni),
                format_func=lambda ident: (
                    f"{MESI[int(opzioni[ident]['month']) - 1]} · "
                    f"{nomi_id.get(opzioni[ident]['principal_id'], 'Mandante')} · "
                    f"{euro(D(str(opzioni[ident]['amount'])))} · {ident[:8]}"),
                key="fatturato_elimina_scelta")
            conferma = st.checkbox("Confermo l'eliminazione definitiva di questa registrazione")
            if st.button("Elimina importo", disabled=not conferma):
                try:
                    anno_aperto(client, anno)
                    elimina_fatturato(client, anno["id"], selezione)
                except Exception:
                    st.error("Eliminazione non confermata: controlla la tabella.")
                else:
                    st.rerun()


def mostra_imposte(client, anno: dict) -> None:
    """Inserimento manuale senza valori precompilati di prova."""
    st.subheader("Imposte · parametri da confermare")
    st.warning("I parametri fiscali del 2027 non sono ancora verificati. Inserisci soltanto valori documentati e concorda massimali, aliquote e deducibilità con il commercialista prima di usarli per decisioni fiscali.")
    try:
        presenti = leggi_parametri(client, anno["id"])
    except Exception:
        st.error("Impossibile leggere i parametri fiscali. Nessuna modifica effettuata.")
        return
    for gruppo, voci in GRUPPI:
        st.markdown(f"### {gruppo}")
        st.dataframe([{
            "Parametro": descrizione.replace(" · scenario", "").replace(" · scenario, da aggiornare", ""),
            "Valore configurato": _formato(presenti[codice]["value"], presenti[codice]["unit"])
                if codice in presenti else "—",
            "Stato": ("Provvisorio" if presenti[codice]["is_provisional"] else "Da verificare con la fonte")
                if codice in presenti else "Non impostato",
        } for codice, descrizione, _esempio, _unita, _cella in voci],
            hide_index=True, width="stretch")
        if anno["status"] != "open":
            continue
        mancanti = {codice: (descrizione, unita) for codice, descrizione, _esempio, unita, _cella
                    in voci if codice not in presenti}
        if mancanti:
            with st.expander(f"Inserisci parametro mancante · {gruppo}"):
                codice = st.selectbox("Parametro da impostare", list(mancanti),
                    format_func=lambda c: mancanti[c][0], key=f"param_nuovo_{voci[0][0]}")
                with st.form(f"param_form_nuovo_{codice}"):
                    testo = st.text_input("Valore (aliquote in decimale: 0,085 = 8,5%)", value="")
                    fonte = st.text_input("Fonte o riferimento del parametro (facoltativo)", value="", max_chars=250)
                    conferma = st.checkbox("Confermo di aver controllato anno, valore e fonte")
                    invia = st.form_submit_button("Salva parametro", type="primary")
                if invia:
                    try:
                        anno_aperto(client, anno)
                        if not conferma:
                            raise ValueError("Conferma anno, importo e fonte prima di salvare.")
                        numero = _numero(testo, mancanti[codice][1])
                        if codice in leggi_parametri(client, anno["id"]):
                            raise ValueError("Parametro già presente: ricarica la pagina prima di riprovare.")
                        risposta = client.table("fiscal_parameters").insert({
                            "fiscal_year_id": anno["id"], "code": codice,
                            "description": mancanti[codice][0], "value": str(numero),
                            "unit": mancanti[codice][1],
                            "source": fonte.strip() or "Inserimento manuale, fonte da verificare",
                            "is_provisional": True,
                        }).execute()
                        if len(risposta.data or []) != 1:
                            raise RuntimeError("Inserimento non confermato")
                    except ValueError as exc:
                        st.warning(str(exc))
                    except Exception:
                        st.error("Salvataggio non confermato: controlla i parametri prima di riprovare.")
                    else:
                        st.rerun()
        modificabili = {codice: descrizione for codice, descrizione, _esempio, _unita, _cella
                       in voci if codice in presenti}
        if modificabili:
            with st.expander(f"Modifica parametro · {gruppo}"):
                codice = st.selectbox("Parametro", list(modificabili),
                    format_func=lambda c: modificabili[c], key=f"param_mod_{voci[0][0]}")
                record = presenti[codice]
                with st.form(f"param_mod_form_{codice}"):
                    testo = st.text_input("Nuovo valore (aliquote in forma decimale)",
                                          value=str(record["value"]).replace(".", ","))
                    conferma = st.checkbox("Confermo la modifica del parametro")
                    invia = st.form_submit_button("Salva modifica")
                if invia:
                    try:
                        anno_aperto(client, anno)
                        if not conferma:
                            raise ValueError("Conferma la modifica prima di salvare.")
                        _modifica(client, anno["id"], record, _numero(testo, record["unit"]))
                    except ValueError as exc:
                        st.warning(str(exc))
                    except Exception:
                        st.error("Modifica non confermata: controlla la tabella.")
                    else:
                        st.rerun()
    if anno["status"] != "open":
        st.info("Anno chiuso: parametri in sola lettura.")
    st.caption("Le registrazioni dei contributi effettivamente versati si gestiscono nel registro sottostante. Un parametro stimato non equivale a un debito o a un versamento confermato.")


def mostra_auto(client, anno: dict) -> None:
    """Vista mensile e contratto, senza gestione di dati dimostrativi."""
    from auto_carburante import _euro
    st.divider()
    st.subheader("Riepilogo Auto")
    try:
        veicolo = auto_unica(_veicoli(client))
        veicolo_id = veicolo["id"] if veicolo else None
        km = _chilometri(client, anno["id"], veicolo_id) if veicolo_id else []
        spese = (leggi_tutti(client, "costs", fiscal_year_id=anno["id"], vehicle_id=veicolo_id)
                 if veicolo_id else [])
        categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])
        impostazioni = _leggi_impostazioni(client, anno["id"], veicolo_id) if veicolo_id else None
        vista = costruisci_tabella_auto(km, spese, categorie, impostazioni)
        limite_penale = riepilogo_limite_penale(km, impostazioni)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere il riepilogo Auto. Nessun dato modificato.")
        return
    if ((veicolo and veicolo.get("notes") == NOTA_VEICOLO_TEST)
            or any(str(r.get("notes") or "").startswith("DATI DI PROVA") for r in [*km, *spese])
            or (impostazioni and str(impostazioni.get("notes") or "").startswith("DATI DI PROVA"))):
        st.warning("Sono ancora presenti registrazioni auto dimostrative. Verifica la pulizia del database.")
    st.table(vista)
    st.caption("Le spese dello stesso mese vengono sommate. Stima annua = totale dei mesi compilati ÷ mesi compilati × 12.")
    st.subheader("Limite chilometrico e penale")
    st.write(" · ".join(f"**{nome}:** {valore}" for nome, valore in limite_penale.items()))
    st.caption("La penale è una stima contrattuale, non una spesa pagata.")
    if anno["status"] != "open" or not veicolo or veicolo.get("notes") == NOTA_VEICOLO_TEST:
        if not veicolo:
            st.caption("Per configurare il limite, registra prima un dato effettivo dell'auto nella maschera in alto.")
        return
    with st.expander("Imposta o modifica limite contrattuale e tariffa"):
        with st.form(f"limite_operativo_{anno['id']}_{veicolo['id']}"):
            limite_testo = st.text_input("Limite chilometrico annuale (km)",
                value=str(impostazioni["annual_km_limit"]).replace(".", ",")
                    if impostazioni and impostazioni.get("annual_km_limit") is not None else "")
            tariffa_testo = st.text_input("Penale per chilometro eccedente (€)",
                value=str(impostazioni["excess_km_penalty"]).replace(".", ",")
                    if impostazioni and impostazioni.get("excess_km_penalty") is not None else "")
            conferma = st.checkbox("Confermo che limite e tariffa corrispondono al contratto")
            salva = st.form_submit_button("Salva parametri contrattuali", type="primary")
        if salva:
            try:
                anno_aperto(client, anno)
                if not conferma:
                    raise ValueError("Conferma i dati contrattuali prima di salvare.")
                limite = importo_valido(limite_testo)
                tariffa = importo_valido(tariffa_testo)
                if limite <= 0:
                    raise ValueError("Il limite deve essere maggiore di zero.")
                dati = {"annual_km_limit": str(limite), "excess_km_penalty": str(tariffa),
                        "notes": "Parametri contrattuali inseriti manualmente"}
                if impostazioni:
                    richiesta = (client.table("vehicle_year_settings").update(dati)
                        .eq("id", impostazioni["id"]).eq("fiscal_year_id", anno["id"])
                        .eq("vehicle_id", veicolo["id"])
                        .eq("annual_km_limit", impostazioni["annual_km_limit"]))
                else:
                    richiesta = client.table("vehicle_year_settings").insert({
                        **dati, "fiscal_year_id": anno["id"], "vehicle_id": veicolo["id"]})
                risposta = richiesta.execute()
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Operazione non confermata")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception:
                st.error("Salvataggio non confermato: controlla il contratto prima di riprovare.")
            else:
                st.rerun()
