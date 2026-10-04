# Fatturato lordo IVA — checkpoint 2026-10-04

Branch feature/fatturato-lordo-iva, base 346f57ba544cead5e4d8a37c6ab4126a21f06097. Frontend ordinario: dialog importo lordo al 22%, anteprima netto e IVA, scorporo con centesimi interi. Le tabelle e tutte le formule restano sul netto. 2026 invariato. Registro IVA vendite documentata in details chiuso, conserva tutti i campi e dati. Nessuna creazione automatica di documenti IVA.

Lordo originale conservato atomicamente nelle note del medesimo record monthly_revenues con marker PIVA_GROSS_22_V1; note precedenti conservate. Backend valida la coerenza lordo/netto con Decimal. Record storici senza marker: precompilazione netto * 1.22, nessuna migrazione. Backup raw include note/lordo originale. Controlli di anno chiuso e concorrenza esistenti mantenuti.

52 test Python e 15 JS/Pyodide passati, build passato. Prossimo passo: pubblicare branch in collaudo demo, verificare salvataggio 1220 -> 1000 + 220, riapertura, centesimi, 2026 e registro espandibile; poi CI e produzione. Non modificare dati reali per verificare.