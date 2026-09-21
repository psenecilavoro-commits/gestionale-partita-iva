"""Calcoli documentali puri. Nessun parametro 2027 è fiscalmente validato."""
from datetime import date
from decimal import Decimal as D
from registri import denaro
from contributi_versati import e_contributo, dati_contributo


def data_anno(valore, anno, oggi=None):
    giorno = date.fromisoformat(str(valore))
    if giorno.year != anno or giorno > (oggi or date.today()):
        raise ValueError("La data deve appartenere all'anno selezionato e non essere futura.")
    return giorno


def valida_vendita(dati, anno, oggi=None):
    r = dict(dati)
    for campo in ("principal_id", "invoice_number"):
        r[campo] = str(r[campo]).strip()
        if not r[campo] or len(r[campo]) > 100:
            raise ValueError("Mandante e numero documento sono obbligatori (numero massimo 100 caratteri).")
    data_anno(r["invoice_date"], anno, oggi)
    if r["document_type"] not in ("fattura", "nota_credito") or not 1 <= int(r["vat_month"]) <= 12:
        raise ValueError("Tipo documento o mese IVA non valido.")
    for campo in ("taxable_amount", "vat_amount"):
        r[campo] = str(denaro(r[campo]))
    # Nota credito: importi positivi nel registro, segno applicato una sola volta.
    return r


def saldo_iva(vendite, acquisti, periodo):
    """Prospetto documentale; il credito iniziale è confermato, mai concatenato da bozze."""
    da, a = int(periodo["month_from"]), int(periodo["month_to"])
    if not 1 <= da <= a <= 12:
        raise ValueError("Periodo IVA non valido.")
    if any(r.get("vat_month") is None or r["document_type"] not in ("fattura", "nota_credito")
           or not 1 <= int(r["vat_month"]) <= 12 for r in vendite):
        raise ValueError("Documento IVA vendite incoerente.")
    if any(denaro(r["deductible_vat"]) > denaro(r["vat_amount"]) for r in acquisti):
        raise ValueError("IVA detraibile superiore all'IVA del documento.")
    emessa = sum((denaro(r["vat_amount"]) * (-1 if r["document_type"] == "nota_credito" else 1)
                  for r in vendite if da <= int(r["vat_month"]) <= a), D(0))
    from iva_acquisti import periodo_fattura
    detraibile = sum((denaro(r["deductible_vat"]) for r in acquisti
                     if da <= periodo_fattura(r)[1] <= a), D(0))
    if not periodo["documents_complete"]:
        return {"vendite": emessa, "acquisti": detraibile, "saldo": None}
    saldo = (emessa - detraibile - denaro(periodo["opening_credit"])
             + denaro(periodo["adjustment"], negativo=True)
             + denaro(periodo["interest_amount"]))
    return {"vendite": emessa, "acquisti": detraibile, "saldo": saldo,
            "debito_prospetto": max(saldo, D(0)), "credito_prospetto": max(-saldo, D(0)),
            "residuo": max(saldo, D(0)) - denaro(periodo["paid_amount"])}


def contributi_per_cassa(righe, anno, oggi=None):
    risultato = {"INPS": D(0), "ENASARCO": D(0), "INPS_AP": D(0)}
    for r in righe:
        if not e_contributo(r):
            continue
        tipo, competenza = dati_contributo(r)
        data_anno(r["payment_date"], anno, oggi)
        if competenza > anno:
            raise ValueError("Competenza successiva al pagamento.")
        importo = denaro(r["amount"])
        risultato[tipo] += importo
        if tipo == "INPS" and competenza < anno:
            risultato["INPS_AP"] += importo
    return risultato


def scenario_cassa(ricavi, costi_deducibili, contributi, pensione, limite_pensione, p):
    """Variante esplicita a cassa, distinta dalla riproduzione letterale del foglio.

    INPS A.P. è già nel totale INPS. Enasarco è sottratto una volta nella
    base, mai dal fatturato. Nessuna stima INPS viene dedotta come versamento.
    """
    pensione_deducibile = min(denaro(pensione), denaro(limite_pensione))
    base = (denaro(ricavi) - denaro(costi_deducibili)
            - denaro(contributi["INPS"]) - denaro(contributi["ENASARCO"]) - pensione_deducibile)
    from imposte_irpef import calcola_irpef_foglio
    # Conserva la base negativa come perdita; nessuna imposta negativa nella variante.
    _, irpef, regionale, comunale, totale = calcola_irpef_foglio(
        max(base, D(0)), D(0), D(0), D(0), D(0), D(0),
        *(p[k] for k in ("irpef_aliquota_1_foglio", "irpef_soglia_2_foglio",
                         "irpef_aliquota_2_foglio", "irpef_soglia_3_foglio",
                         "irpef_aliquota_3_foglio", "addizionale_veneto_foglio",
                         "addizionale_verona_foglio")))
    return {"fatturato": denaro(ricavi), "base": base, "pensione": pensione_deducibile,
            "irpef": irpef, "regionale": regionale, "comunale": comunale, "totale": totale}


def valida_periodo(r, anno, altri, oggi=None):
    da, a = int(r["month_from"]), int(r["month_to"])
    modalita = r["frequency"]
    if modalita == "mensile":
        valido = 1 <= da <= 12 and da == a
    else:
        valido = modalita == "trimestrale" and da in (1, 4, 7, 10) and a == da + 2
    if not valido:
        raise ValueError("Seleziona un mese o un trimestre intero.")
    if any(da <= int(x["month_to"]) and a >= int(x["month_from"]) for x in altri):
        raise ValueError("Periodo sovrapposto a un prospetto già presente.")
    for campo in ("opening_credit", "interest_amount", "paid_amount"):
        denaro(r[campo])
    denaro(r["adjustment"], negativo=True)
    if denaro(r["paid_amount"]) > 0:
        if not r.get("payment_date"):
            raise ValueError("Indica la data del versamento effettivo.")
        giorno = date.fromisoformat(str(r["payment_date"]))
        if giorno > (oggi or date.today()):
            raise ValueError("Il versamento non può essere futuro.")
    elif r.get("payment_date"):
        raise ValueError("Una data di pagamento richiede un versamento positivo.")
    return dict(r)
