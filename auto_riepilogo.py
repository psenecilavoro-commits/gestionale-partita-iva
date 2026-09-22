"""Vista unica mensile dell'auto; legge soltanto i registri già esistenti.

Limite chilometrico e penale sono un'unica voce annuale sotto la tabella,
non colonne mensili. Nessuna modifica a dati o formule fiscali.
"""
from collections import defaultdict
from decimal import Decimal

import streamlit as st
from supabase import Client

from auto import NOTA_VEICOLO_TEST, _chilometri, _formato_km, _veicoli, auto_unica
from auto_limiti import _leggi_impostazioni, calcola_sforamento, mostra_limiti_auto
from auto_carburante import _euro
from fatturato import MESI
from registri import leggi_tutti

D = Decimal
CATEGORIE_AUTO = ("carburante", "autostrada", "rate_auto")
COLONNE = ("Mese", "Percorrenza", "Carburante", "Autostrada", "Rate auto")


def _mese_spesa(spesa: dict) -> int:
    mese = int(str(spesa["expense_date"])[5:7])
    if not 1 <= mese <= 12:
        raise ValueError("Mese della spesa auto non valido.")
    return mese


def costruisci_tabella_auto(chilometri: list[dict], spese: list[dict],
                            categorie: list[dict], impostazioni: dict | None) -> list[dict]:
    """Dodici mesi e due righe di riepilogo, senza duplicare spese o limiti.

    Lo zero di un mese compilato è distinto dal mese non ancora compilato.
    Le spese multiple nello stesso mese contribuiscono una volta alla media.
    Il parametro impostazioni resta accettato per compatibilità con i chiamanti.
    """
    km_mesi = {}
    for riga in chilometri:
        mese = int(riga["month"])
        if not 1 <= mese <= 12 or mese in km_mesi:
            raise ValueError("Percorrenza mensile non valida o duplicata.")
        km_mesi[mese] = D(str(riga["distance_km"]))

    codici = {riga["id"]: riga["code"] for riga in categorie
              if riga.get("code") in CATEGORIE_AUTO}
    importi = {codice: defaultdict(lambda: D("0")) for codice in CATEGORIE_AUTO}
    for riga in spese:
        codice = codici.get(riga["category_id"])
        if codice is not None:
            importi[codice][_mese_spesa(riga)] += D(str(riga["gross_amount"]))

    campi = (("carburante", "Carburante"), ("autostrada", "Autostrada"),
             ("rate_auto", "Rate auto"))
    righe = []
    for mese in range(1, 13):
        riga = {"Mese": MESI[mese - 1],
                "Percorrenza": _formato_km(km_mesi[mese]) if mese in km_mesi else "—"}
        for codice, etichetta in campi:
            riga[etichetta] = _euro(importi[codice][mese]) if mese in importi[codice] else "—"
        righe.append(riga)

    km_totali = sum(km_mesi.values(), D("0"))
    previsto_km = km_totali / len(km_mesi) * 12 if km_mesi else None
    registrato = {"Mese": "Totale registrato",
                  "Percorrenza": _formato_km(km_totali) if km_mesi else "—"}
    previsto = {"Mese": "Stima annua",
                "Percorrenza": _formato_km(previsto_km) if previsto_km is not None else "—"}
    for codice, etichetta in campi:
        mesi = importi[codice]
        registrato[etichetta] = _euro(sum(mesi.values(), D("0"))) if mesi else "—"
        previsto[etichetta] = _euro(sum(mesi.values(), D("0")) / len(mesi) * 12) if mesi else "—"
    righe.extend([registrato, previsto])
    return [{colonna: riga[colonna] for colonna in COLONNE} for riga in righe]


def riepilogo_limite_penale(chilometri: list[dict], impostazioni: dict | None) -> dict[str, str]:
    """Rappresenta i parametri contrattuali senza scambiarli per costi pagati.

    Riutilizza la stessa funzione di calcolo della penale della sezione Auto.
    """
    limite_raw = impostazioni.get("annual_km_limit") if impostazioni else None
    tariffa_raw = impostazioni.get("excess_km_penalty") if impostazioni else None
    limite = D(str(limite_raw)) if limite_raw is not None else None
    tariffa = D(str(tariffa_raw)) if tariffa_raw is not None else None
    risultato = {
        "Limite annuo": _formato_km(limite) if limite is not None else "—",
        "Tariffa per km eccedente": _euro(tariffa) if tariffa is not None else "—",
        "Penale su km registrati": "—",
        "Penale su km stimati": "—",
    }
    if not chilometri or limite is None or tariffa is None:
        return risultato
    km_totali = sum((D(str(riga["distance_km"])) for riga in chilometri), D("0"))
    km_stimati = km_totali / len(chilometri) * 12
    risultato["Penale su km registrati"] = _euro(calcola_sforamento(km_totali, limite, tariffa)[1])
    risultato["Penale su km stimati"] = _euro(calcola_sforamento(km_stimati, limite, tariffa)[1])
    return risultato


def mostra_riepilogo_auto(client: Client, anno: dict) -> None:
    st.divider()
    st.subheader("Riepilogo Auto")
    try:
        veicolo = auto_unica(_veicoli(client))
        veicolo_id = veicolo["id"] if veicolo else None
        chilometri = _chilometri(client, anno["id"], veicolo_id) if veicolo_id else []
        spese = (leggi_tutti(client, "costs", fiscal_year_id=anno["id"],
                            vehicle_id=veicolo_id) if veicolo_id else [])
        categorie = leggi_tutti(client, "cost_categories", fiscal_year_id=anno["id"])
        impostazioni = (_leggi_impostazioni(client, anno["id"], veicolo_id)
                        if veicolo_id else None)
        tabella = costruisci_tabella_auto(chilometri, spese, categorie, impostazioni)
        limite_penale = riepilogo_limite_penale(chilometri, impostazioni)
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Impossibile leggere il riepilogo Auto. Nessun dato modificato.")
        return

    if ((veicolo and veicolo.get("notes") == NOTA_VEICOLO_TEST)
            or any(str(r.get("notes") or "").startswith("DATI DI PROVA")
                   for r in [*chilometri, *spese])
            or (impostazioni and str(impostazioni.get("notes") or "").startswith("DATI DI PROVA"))):
        st.warning("Sono presenti dati di prova: non rappresentano percorrenze o spese effettive.")
    st.table(tabella)
    st.caption("Le spese dello stesso mese vengono sommate. Stima annua = totale dei mesi "
               "compilati ÷ numero di mesi compilati × 12.")

    st.subheader("Limite chilometrico e penale")
    st.write(" · ".join(f"**{voce}:** {valore}" for voce, valore in limite_penale.items()))
    if not impostazioni:
        st.caption("Nessun limite e nessuna tariffa registrati per l'anno selezionato.")
    else:
        st.caption("La penale è un confronto contrattuale stimato, non una spesa effettivamente pagata. "
                   "Non viene calcolata se mancano il limite, la tariffa o i chilometri.")
    # Mantieni accessibili i comandi dimostrativi preesistenti senza un altro
    # prospetto visibile nella schermata principale.
    if veicolo and veicolo.get("notes") == NOTA_VEICOLO_TEST:
        with st.expander("Gestisci limite e penale di prova"):
            mostra_limiti_auto(client, anno)
