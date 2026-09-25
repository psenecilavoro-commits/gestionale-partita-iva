"""Registro e piano ammortamenti dei beni strumentali."""
from datetime import date
from decimal import Decimal as D, ROUND_HALF_UP

import streamlit as st

from fatturato import euro, importo_valido
from registri import leggi_tutti, anno_aperto

SOGLIA_BENE_MINORE = D("516.46")
CENT = D("0.01")


def quota_ammortamento(costo_fiscale: D, coefficiente: D,
                       anno_acquisto: int, anno: int) -> tuple[D, D]:
    """Restituisce quota dell'anno e fondo a fine anno senza superare il costo."""
    if costo_fiscale < 0 or coefficiente < 0 or coefficiente > D("1") or anno < anno_acquisto:
        return D("0"), D("0")
    if costo_fiscale <= SOGLIA_BENE_MINORE:
        return ((costo_fiscale, costo_fiscale)
                if anno == anno_acquisto else (D("0"), costo_fiscale))
    fondo = D("0")
    quota_anno = D("0")
    for y in range(anno_acquisto, anno + 1):
        aliquota = coefficiente / D("2") if y == anno_acquisto else coefficiente
        quota = min(costo_fiscale * aliquota, max(costo_fiscale - fondo, D("0")))
        fondo += quota
        if y == anno:
            quota_anno = quota
        if fondo >= costo_fiscale:
            break
    return quota_anno, fondo


def calcola_bene(r: dict, anno: int) -> dict:
    lordo = D(str(r["gross_amount"]))
    iva_det = D(str(r["deductible_vat"]))
    costo = max(lordo - iva_det, D("0"))
    coeff = D(str(r["depreciation_rate"]))
    primo = int(r["first_fiscal_year"])
    quota, fondo = quota_ammortamento(costo, coeff, primo, anno)
    return {
        "costo_fiscale": costo,
        "quota": quota,
        "fondo": fondo,
        "residuo": max(costo - fondo, D("0")),
    }


def _fmt(v: D) -> str:
    return euro(v.quantize(CENT, rounding=ROUND_HALF_UP))


def _leggi(client):
    return leggi_tutti(client, "depreciable_assets")


def _previsto(r: dict) -> bool:
    return bool(r.get("is_planned", False))


def _coefficiente(testo: str, costo_fiscale: D) -> D:
    """Sotto soglia il coefficiente non serve; in DB salviamo 100% come valore tecnico."""
    if costo_fiscale <= SOGLIA_BENE_MINORE:
        return D("1")
    if not testo.strip():
        raise ValueError("Per un costo fiscale superiore a 516,46 € inserisci il coefficiente di ammortamento.")
    try:
        valore = D(testo.strip().replace(",", ".")) / D("100")
    except Exception as exc:
        raise ValueError("Inserisci un coefficiente valido, ad esempio 20.") from exc
    if valore <= 0 or valore > D("1"):
        raise ValueError("Il coefficiente deve essere maggiore di 0 e non oltre 100%.")
    return valore


def mostra_ammortamenti(client, anno: dict) -> None:
    anno_num = int(anno["fiscal_year"])
    st.subheader(f"Ammortamenti · {anno_num}")
    st.caption(
        "Costo fiscale = esborso lordo − IVA detraibile. Fino a 516,46 € la deduzione "
        "è integrale nell'anno e il coefficiente non è necessario; oltre la soglia "
        "si applica il coefficiente, dimezzato nel primo anno."
    )
    try:
        beni = _leggi(client)
    except Exception as exc:
        if str(getattr(exc, "code", "")) in ("42P01", "PGRST205", "42703", "PGRST204"):
            st.info(
                "La sezione richiede la versione aggiornata di SQL_AMMORTAMENTI.sql "
                "nel Supabase dedicato al Gestionale Partita IVA."
            )
        else:
            st.error("Registro ammortamenti non accessibile.")
        return

    attivi = []
    totale_effettivo = D("0")
    totale_previsto = D("0")
    for r in beni:
        primo = int(r["first_fiscal_year"])
        if primo > anno_num:
            continue
        calc = calcola_bene(r, anno_num)
        if calc["quota"] == 0 and calc["residuo"] == 0:
            continue
        previsto = _previsto(r)
        if previsto:
            totale_previsto += calc["quota"]
        else:
            totale_effettivo += calc["quota"]
        attivi.append({
            "Bene": r["description"],
            "Tipo": "Previsto" if previsto else "Acquistato",
            "Data": r["purchase_date"],
            "Costo lordo": _fmt(D(str(r["gross_amount"]))),
            "IVA detraibile": _fmt(D(str(r["deductible_vat"]))),
            "Costo fiscale": _fmt(calc["costo_fiscale"]),
            "Coefficiente": (
                "Integrale"
                if calc["costo_fiscale"] <= SOGLIA_BENE_MINORE
                else f"{D(str(r['depreciation_rate'])) * 100:g}%"
            ),
            "Quota anno": _fmt(calc["quota"]),
            "Fondo": _fmt(calc["fondo"]),
            "Residuo": _fmt(calc["residuo"]),
        })

    if attivi:
        st.dataframe(attivi, hide_index=True, width="stretch")
    else:
        st.info("Nessun ammortamento attivo nell'anno selezionato.")

    c1, c2 = st.columns(2)
    c1.metric("Quota fiscalmente deducibile · beni acquistati", _fmt(totale_effettivo))
    c2.metric("Quota prevista · simulazione", _fmt(totale_previsto))
    st.caption(
        "I beni previsti sono soltanto una simulazione e non entrano nella quota "
        "fiscalmente deducibile finché non vengono confermati come acquistati."
    )

    if anno["status"] != "open":
        st.info("Anno chiuso: registro in sola lettura.")
        return

    with st.expander("➕ Registra un bene strumentale"):
        with st.form(f"amm_new_{anno_num}", clear_on_submit=True):
            tipo = st.radio(
                "Tipo di inserimento",
                ("Acquistato", "Previsto"),
                horizontal=True,
                help="Previsto consente di pianificare anche un acquisto con data futura.",
            )
            descr = st.text_input("Descrizione bene")
            acquisto = st.date_input(
                "Data acquisto" if tipo == "Acquistato" else "Data acquisto prevista",
                value=date(anno_num, 1, 1),
                min_value=date(anno_num, 1, 1),
                max_value=date(anno_num, 12, 31),
            )
            lordo_txt = st.text_input(
                "Esborso lordo (€)" if tipo == "Acquistato" else "Esborso lordo previsto (€)"
            )
            iva_txt = st.text_input(
                "IVA detraibile (€; 0 se non detraibile)",
                value="0",
            )
            coeff_txt = st.text_input(
                "Coefficiente ammortamento (%) · solo se costo fiscale > 516,46 €",
                placeholder="es. 20; lascia vuoto sotto soglia",
            )
            note = st.text_input("Note facoltative", max_chars=500)
            ok = st.checkbox(
                "Confermo importi, IVA, classificazione e coefficiente quando necessario"
            )
            salva = st.form_submit_button("Salva bene", type="primary")

        if salva:
            try:
                anno_aperto(client, anno)
                if not ok:
                    raise ValueError("Conferma prima i dati del bene.")
                nome = " ".join(descr.split())
                if not nome or len(nome) > 200:
                    raise ValueError("Inserisci una descrizione valida.")
                previsto = tipo == "Previsto"
                if not previsto and acquisto > date.today():
                    raise ValueError(
                        "Un bene acquistato non può avere una data futura. "
                        "Se si tratta di una previsione, seleziona «Previsto»."
                    )
                lordo = importo_valido(lordo_txt)
                iva = importo_valido(iva_txt)
                if iva > lordo:
                    raise ValueError("L'IVA detraibile non può superare l'esborso lordo.")
                costo_fiscale = lordo - iva
                coeff = _coefficiente(coeff_txt, costo_fiscale)
                risposta = client.table("depreciable_assets").insert({
                    "fiscal_year_id": anno["id"],
                    "description": nome,
                    "purchase_date": acquisto.isoformat(),
                    "gross_amount": str(lordo),
                    "deductible_vat": str(iva),
                    "depreciation_rate": str(coeff),
                    "first_fiscal_year": anno_num,
                    "is_planned": previsto,
                    "notes": note.strip() or None,
                }).execute()
                if len(risposta.data or []) != 1:
                    raise RuntimeError("Salvataggio non confermato")
            except ValueError as exc:
                st.warning(str(exc))
            except Exception as exc:
                if str(getattr(exc, "code", "")) in ("42703", "PGRST204"):
                    st.error(
                        "Il database non ha ancora il campo Previsto/Acquistato: "
                        "riesegui SQL_AMMORTAMENTI.sql aggiornato e riprova."
                    )
                else:
                    st.error("Salvataggio non confermato: controlla il registro.")
            else:
                st.rerun()

    propri = [r for r in beni if int(r["first_fiscal_year"]) == anno_num]
    previsti_confermabili = [
        r for r in propri
        if _previsto(r) and date.fromisoformat(str(r["purchase_date"])) <= date.today()
    ]
    if previsti_confermabili:
        with st.expander("Conferma l'acquisto di un bene previsto"):
            indice = {r["id"]: r for r in previsti_confermabili}
            scelto = st.selectbox(
                "Bene previsto",
                list(indice),
                format_func=lambda k: (
                    f"{indice[k]['description']} · {indice[k]['purchase_date']}"
                ),
                key=f"amm_confirm_{anno_num}",
            )
            conferma = st.checkbox(
                "Confermo che il bene è stato realmente acquistato",
                key=f"amm_confirm_ok_{anno_num}",
            )
            if st.button(
                "Segna come acquistato",
                disabled=not conferma,
                key=f"amm_confirm_btn_{anno_num}",
            ):
                r = indice[scelto]
                try:
                    anno_aperto(client, anno)
                    esito = (
                        client.table("depreciable_assets")
                        .update({"is_planned": False})
                        .eq("id", r["id"])
                        .eq("fiscal_year_id", anno["id"])
                        .execute()
                    )
                    if len(esito.data or []) != 1:
                        raise RuntimeError()
                except Exception:
                    st.error("Conferma dell'acquisto non riuscita.")
                else:
                    st.rerun()

    if propri:
        with st.expander("Elimina un bene inserito nell'anno"):
            indice = {r["id"]: r for r in propri}
            scelto = st.selectbox(
                "Bene",
                list(indice),
                format_func=lambda k: (
                    f"{indice[k]['description']} · "
                    f"{'Previsto' if _previsto(indice[k]) else 'Acquistato'}"
                ),
                key=f"amm_del_{anno_num}",
            )
            conferma = st.checkbox(
                "Confermo l'eliminazione definitiva",
                key=f"amm_ok_{anno_num}",
            )
            if st.button(
                "Elimina bene",
                disabled=not conferma,
                key=f"amm_btn_{anno_num}",
            ):
                r = indice[scelto]
                try:
                    anno_aperto(client, anno)
                    esito = (
                        client.table("depreciable_assets")
                        .delete()
                        .eq("id", r["id"])
                        .eq("fiscal_year_id", anno["id"])
                        .execute()
                    )
                    if len(esito.data or []) != 1:
                        raise RuntimeError()
                except Exception:
                    st.error("Eliminazione non confermata.")
                else:
                    st.rerun()
