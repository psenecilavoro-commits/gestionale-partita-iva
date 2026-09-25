"""Calcoli fiscali puri usati dai prospetti previsionali.

Le aliquote e le soglie arrivano sempre da fiscal_parameters: questo modulo
non rende definitivo alcun parametro 2027. Le funzioni separano:
- reddito d'impresa / imponibile contributivo;
- contributi stimati;
- contributi effettivamente versati, che competono alla base IRPEF per cassa;
- detrazioni, che riducono l'imposta e non la base.
"""
from decimal import Decimal as D


def _ok(*valori: D) -> None:
    if any(not v.is_finite() or v < 0 for v in valori):
        raise ValueError("Importi, soglie e aliquote devono essere finiti e non negativi.")


def deduzione_agenti(reddito: D, soglia1: D, aliquota1: D,
                     soglia2: D, aliquota2: D,
                     soglia3: D, aliquota3: D) -> D:
    """Deduzione a scaglioni del modello definitivo del foglio.

    Il calcolo è progressivo e si arresta alla terza soglia. Non modifica il
    fatturato: riduce soltanto il reddito d'impresa usato nelle basi fiscali.
    """
    valori = (reddito, soglia1, aliquota1, soglia2, aliquota2, soglia3, aliquota3)
    _ok(*valori)
    if not D("0") < soglia1 < soglia2 < soglia3:
        raise ValueError("Soglie della deduzione agenti non coerenti.")
    if any(a > D("1") for a in (aliquota1, aliquota2, aliquota3)):
        raise ValueError("Aliquota della deduzione agenti non coerente.")
    base = max(reddito, D("0"))
    primo = min(base, soglia1) * aliquota1
    secondo = max(min(base, soglia2) - soglia1, D("0")) * aliquota2
    terzo = max(min(base, soglia3) - soglia2, D("0")) * aliquota3
    return primo + secondo + terzo


def calcola_inps_previsionale(fatturato: D, costi_deducibili: D, *,
                              fisso: D, minimale: D, aliquota_prima: D,
                              soglia_seconda: D, aliquota_seconda: D,
                              massimale: D, agenti: tuple[D, D, D, D, D, D]) -> dict[str, D]:
    """INPS del modello: Enasarco NON viene sottratto dall'imponibile INPS."""
    _ok(fatturato, costi_deducibili, fisso, minimale, aliquota_prima,
        soglia_seconda, aliquota_seconda, massimale)
    if not minimale <= soglia_seconda <= massimale:
        raise ValueError("Soglie INPS non coerenti.")
    if aliquota_prima > 1 or aliquota_seconda > 1:
        raise ValueError("Aliquote INPS non coerenti.")
    reddito_prima_deduzione = max(fatturato - costi_deducibili, D("0"))
    deduzione = deduzione_agenti(reddito_prima_deduzione, *agenti)
    imponibile = max(reddito_prima_deduzione - deduzione, D("0"))
    if imponibile <= minimale:
        eccedente = D("0")
    else:
        limitato = min(imponibile, massimale)
        if limitato <= soglia_seconda:
            eccedente = (limitato - minimale) * aliquota_prima
        else:
            eccedente = ((soglia_seconda - minimale) * aliquota_prima
                         + (limitato - soglia_seconda) * aliquota_seconda)
    return {
        "reddito_prima_deduzione": reddito_prima_deduzione,
        "deduzione_agenti": deduzione,
        "imponibile_inps": imponibile,
        "inps_eccedente": eccedente,
        "inps_totale": fisso + eccedente,
    }


def calcola_irpef_da_base(base: D, *, aliquota1: D, soglia2: D, aliquota2: D,
                           soglia3: D, aliquota3: D,
                           addizionale_regionale: D, addizionale_comunale: D) -> dict[str, D]:
    """IRPEF progressiva e addizionali su una base già determinata."""
    _ok(base, aliquota1, soglia2, aliquota2, soglia3, aliquota3,
        addizionale_regionale, addizionale_comunale)
    if not D("0") < soglia2 < soglia3:
        raise ValueError("Soglie IRPEF non coerenti.")
    if any(a > D("1") for a in
           (aliquota1, aliquota2, aliquota3, addizionale_regionale, addizionale_comunale)):
        raise ValueError("Aliquote IRPEF/addizionali non coerenti.")
    imponibile = max(base, D("0"))
    primo = min(imponibile, soglia2) * aliquota1
    secondo = max(min(imponibile, soglia3) - soglia2, D("0")) * aliquota2
    terzo = max(imponibile - soglia3, D("0")) * aliquota3
    irpef = primo + secondo + terzo
    regionale = imponibile * addizionale_regionale
    comunale = imponibile * addizionale_comunale
    return {
        "imponibile_irpef": imponibile,
        "irpef_lorda": irpef,
        "addizionale_regionale": regionale,
        "addizionale_comunale": comunale,
        "imposte_lorde": irpef + regionale + comunale,
    }


def parametri_agenti(p: dict[str, D]) -> tuple[D, D, D, D, D, D]:
    return tuple(p[k] for k in (
        "agenti_soglia_1_foglio", "agenti_aliquota_1_foglio",
        "agenti_soglia_2_foglio", "agenti_aliquota_2_foglio",
        "agenti_soglia_3_foglio", "agenti_aliquota_3_foglio",
    ))


def parametri_irpef(p: dict[str, D]) -> dict[str, D]:
    return {
        "aliquota1": p["irpef_aliquota_1_foglio"],
        "soglia2": p["irpef_soglia_2_foglio"],
        "aliquota2": p["irpef_aliquota_2_foglio"],
        "soglia3": p["irpef_soglia_3_foglio"],
        "aliquota3": p["irpef_aliquota_3_foglio"],
        "addizionale_regionale": p["addizionale_veneto_foglio"],
        "addizionale_comunale": p["addizionale_verona_foglio"],
    }


def conto_previsionale(*, fatturato: D, costi_netti: D, costi_deducibili: D,
                       enasarco_stimato: D, contributi_irpef: D,
                       pensione_deducibile: D, detrazioni: D, p: dict[str, D]) -> dict[str, D]:
    """Conto previsionale coerente con le regole concordate.

    Il netto economico sottrae l'INPS stimato e l'Enasarco stimato.
    La base IRPEF, invece, usa SOLO i contributi che il chiamante dichiara
    deducibili per cassa nell'anno (contributi_irpef) e il fondo pensione
    deducibile. Il fondo pensione non viene sottratto di nuovo dal netto.
    """
    _ok(fatturato, costi_netti, costi_deducibili, enasarco_stimato,
        contributi_irpef, pensione_deducibile, detrazioni)
    inps = calcola_inps_previsionale(
        fatturato, costi_deducibili,
        fisso=p["inps_fisso_foglio"], minimale=p["inps_minimale_foglio"],
        aliquota_prima=p["inps_aliquota_prima_foglio"],
        soglia_seconda=p["inps_soglia_seconda_foglio"],
        aliquota_seconda=p["inps_aliquota_seconda_foglio"],
        massimale=p["inps_massimale_foglio"], agenti=parametri_agenti(p),
    )
    base_irpef = (inps["imponibile_inps"] - enasarco_stimato
                  - contributi_irpef - pensione_deducibile)
    imposte = calcola_irpef_da_base(base_irpef, **parametri_irpef(p))
    detrazioni_usate = min(detrazioni, imposte["imposte_lorde"])
    imposte_nette = imposte["imposte_lorde"] - detrazioni_usate
    netto = (fatturato - inps["inps_totale"] - enasarco_stimato
             - costi_netti - imposte_nette)
    netto_no_costi = (fatturato - inps["inps_totale"] - enasarco_stimato
                      - imposte_nette)
    return {
        **inps, **imposte,
        "contributi_irpef_deducibili": contributi_irpef,
        "pensione_deducibile": pensione_deducibile,
        "detrazioni_disponibili": detrazioni,
        "detrazioni_usate": detrazioni_usate,
        "imposte_nette": imposte_nette,
        "netto": netto,
        "netto_mese": netto / D("12"),
        "netto_no_costi": netto_no_costi,
        "netto_no_costi_mese": netto_no_costi / D("12"),
    }
