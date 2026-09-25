"""Regime fiscale applicato alle annualità del gestionale.

Per il progetto personale corrente:
- 2026: regime forfettario;
- dal 2027: regime ordinario.

La funzione è centralizzata per evitare condizioni sparse nell'interfaccia.
"""

def regime_fiscale(anno: dict | int) -> str:
    numero = int(anno["fiscal_year"] if isinstance(anno, dict) else anno)
    return "forfettario" if numero == 2026 else "ordinario"


def e_forfettario(anno: dict | int) -> bool:
    return regime_fiscale(anno) == "forfettario"


def etichetta_regime(anno: dict | int) -> str:
    return "Regime forfettario" if e_forfettario(anno) else "Regime ordinario"
