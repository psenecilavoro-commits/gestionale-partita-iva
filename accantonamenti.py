"""Tabella accantonamenti: provvigioni registrate e somme annotate manualmente.

Nessun calcolo di IVA dovuta, imposte, contributi o netto fiscale: questi
richiedono fatture e parametri verificati. I dati TEST restano riconoscibili.
"""

from decimal import Decimal

import streamlit as st
from supabase import Client

from fatturato import CENT, MESI, NOTA_TEST, euro, importo_valido, leggi_fatturato


def leggi_accantonamenti(client: Client, anno_id: str) -> list[dict]:
    risposta = (
        client.table("monthly_reserves")
        .select("id,month,reserved_amount,notes")
        .eq("fiscal_year_id", anno_id)
        .order("month")
        .execute()
    )
    return risposta.data or []


def calcola_tabella(
    fatturati: list[dict], accantonamenti: list[dict]
) -> tuple[list[dict], Decimal, Decimal, Decimal, int]:
    """Le celle assenti restano assenti; 0 salvato esplicitamente e' presente."""
    ricavi_per_mese: dict[int, Decimal] = {}
    for riga in fatturati:
        mese = int(riga["month"])
        if mese not in range(1, 13):
            raise ValueError("Mese fatturato non valido")
        ricavi_per_mese[mese] = ricavi_per_mese.get(mese, Decimal("0")) + Decimal(str(riga["amount"]))

    riserve_per_mese: dict[int, Decimal] = {}
    for riga in accantonamenti:
        mese = int(riga["month"])
        if mese not in range(1, 13) or mese in riserve_per_mese:
            raise ValueError("Accantonamento duplicato o mese non valido")
        riserve_per_mese[mese] = Decimal(str(riga["reserved_amount"]))

    tabella = []
    rimanenza_mesi_completi = Decimal("0")
    mesi_completi = 0
    for mese, nome in enumerate(MESI, start=1):
        ricavi = ricavi_per_mese.get(mese)
        riserva = riserve_per_mese.get(mese)
        rimanenza = ricavi - riserva if ricavi is not None and riserva is not None else None
        if rimanenza is not None:
            rimanenza_mesi_completi += rimanenza
            mesi_completi += 1
        tabella.append({
            "Mese": nome,
            "Provvigioni IVA esclusa": euro(ricavi) if ricavi is not None else "—",
            "Accantonato (manuale)": euro(riserva) if riserva is not None else "—",
            "Provvigioni meno accantonato": euro(rimanenza) if rimanenza is not None else "—",
        })
    return (
        tabella,
        sum(ricavi_per_mese.values(), Decimal("0")),
        sum(riserve_per_mese.values(), Decimal("0")),
        rimanenza_mesi_completi,
        mesi_completi,
    )


def salva_accantonamento(
    client: Client, anno_id: str, mese: int, importo: Decimal,
    nota: str, esistente: dict | None,
) -> None:
    if (mese not in range(1, 13) or not importo.is_finite()
            or importo < 0 or importo != importo.quantize(CENT)):
        raise ValueError("Mese o importo non valido.")
    campi = {"reserved_amount": str(importo), "notes": nota.strip() or None}
    if esistente is None:
        risposta = client.table("monthly_reserves").insert({
            "fiscal_year_id": anno_id, "month": mese, **campi,
        }).execute()
    else:
        risposta = (
            client.table("monthly_reserves")
            .update(campi)
            .eq("id", esistente["id"])
            .eq("fiscal_year_id", anno_id)
            .eq("month", mese)
            .execute()
        )
    if len(risposta.data or []) != 1:
        raise RuntimeError("Salvataggio non confermato")


def elimina_accantonamento(client: Client, anno_id: str, esistente: dict) -> None:
    risposta = (
        client.table("monthly_reserves")
        .delete()
        .eq("id", esistente["id"])
        .eq("fiscal_year_id", anno_id)
        .eq("month", esistente["month"])
        .execute()
    )
    if len(risposta.data or []) != 1:
        raise RuntimeError("Eliminazione non confermata")


def mostra_accantonamenti(client: Client, anno: dict) -> None:
    st.subheader("Tabella accantonamenti")
    st.caption(
        "Provvigioni lette da Fatturato; accantonamenti inseriti manualmente. "
        "La differenza non è il netto disponibile: IVA, INPS, Enasarco e imposte non sono ancora calcolati."
    )
    try:
        fatturati = leggi_fatturato(client, anno["id"])
        riserve = leggi_accantonamenti(client, anno["id"])
        tabella, totale_ricavi, totale_riserve, rimanenza, mesi_completi = calcola_tabella(fatturati, riserve)
    except Exception:
        st.error("Impossibile leggere gli accantonamenti. Nessun dato modificato.")
        return

    if any(r.get("notes") == NOTA_TEST for r in fatturati):
        st.warning("DATI DI PROVA presenti nel Fatturato: anche le provvigioni qui visualizzate sono una simulazione.")

    st.dataframe(tabella, hide_index=True, width="stretch")
    c1, c2, c3 = st.columns(3)
    c1.metric("Provvigioni registrate", euro(totale_ricavi))
    c2.metric("Accantonamenti annotati", euro(totale_riserve))
    c3.metric(
        "Differenza · mesi completi",
        euro(rimanenza) if mesi_completi else "—",
        help="Somma di provvigioni meno accantonamenti solo per mesi in cui entrambi sono compilati. Non è il netto fiscale.",
    )
    st.caption(
        f"Mesi completi: {mesi_completi}/12. Un mese senza dati non è zero. "
        "Registrare un accantonamento non sposta denaro in banca."
    )
    st.info(
        "IVA fatturata, IVA sugli acquisti e IVA dovuta verranno aggiunte quando potremo "
        "distinguere le fatture effettive dai test e usare le date di ricezione delle fatture di acquisto."
    )

    if anno["status"] != "open":
        st.info("Anno chiuso: accantonamenti in sola lettura.")
        return

    st.markdown("**Aggiungi o modifica un accantonamento**")
    mese_nome = st.selectbox("Mese", MESI, key="accantonamenti_mese")
    mese = MESI.index(mese_nome) + 1
    indice = {int(r["month"]): r for r in riserve}
    esistente = indice.get(mese)
    if esistente is not None:
        st.caption("Questo mese è già presente: salvando modifichi il record esistente senza crearne un secondo.")
    with st.form(f"accantonamento_form_{mese}"):
        importo_testo = st.text_input(
            "Importo accantonato (€)",
            value=str(esistente["reserved_amount"]).replace(".", ",") if esistente else "",
            help="Inserisci un importo effettivamente destinato da te all'accantonamento; 0 è ammesso se intenzionale.",
        )
        nota = st.text_input("Nota facoltativa", value=(esistente.get("notes") or "") if esistente else "")
        invia = st.form_submit_button("Salva accantonamento", type="primary")
    if invia:
        try:
            importo = importo_valido(importo_testo)
            # Un salvataggio senza nota non implica che il denaro sia stato trasferito.
            salva_accantonamento(client, anno["id"], mese, importo, nota, esistente)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Salvataggio non confermato. Controlla la tabella prima di riprovare.")
        else:
            st.rerun()

    if riserve:
        with st.expander("Elimina un accantonamento"):
            opzioni = {
                f"{MESI[int(r['month']) - 1]} · {euro(Decimal(str(r['reserved_amount'])))}": r
                for r in riserve
            }
            scelta = st.selectbox("Accantonamento da eliminare", list(opzioni), key="accantonamenti_elimina_mese")
            conferma = st.checkbox("Confermo l'eliminazione definitiva del mese selezionato", key="accantonamenti_elimina_ok")
            if st.button("Elimina accantonamento", disabled=not conferma, key="accantonamenti_elimina_btn"):
                try:
                    elimina_accantonamento(client, anno["id"], opzioni[scelta])
                except Exception:
                    st.error("Eliminazione non confermata. Controlla la tabella prima di riprovare.")
                else:
                    st.rerun()
