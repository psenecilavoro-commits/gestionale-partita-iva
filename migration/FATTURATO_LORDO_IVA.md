# Fatturato lordo IVA — checkpoint 2026-10-05

Completato tramite PR #22. Branch feature/fatturato-lordo-iva, ultimo commit funzionale aedf3d2949e2a65300d2021c738b73c96f9525c6, merge main 9aa9abcf4a75d909e3082c67fa88c31cd5a08afa.

Frontend ordinario: dialog importo lordo al 22%, anteprima netto e IVA, scorporo con centesimi interi. Le tabelle e tutte le formule restano sul netto. 2026 invariato. Registro IVA vendite documentata in details chiuso, conserva tutti i campi e dati. Nessuna creazione automatica di documenti IVA.

Lordo originale conservato atomicamente nelle note del medesimo record monthly_revenues con marker PIVA_GROSS_22_V1; note precedenti conservate. Backend valida la coerenza lordo/netto con Decimal. Record storici senza marker: precompilazione netto * 1.22, nessuna migrazione. Backup raw include note/lordo originale. Controlli anno chiuso e concorrenza esistenti mantenuti.

52 test Python, 15 JS/Pyodide, build e entrambe CI passati. Browser demo: 1220 -> 1000 + 220, salvataggio e riapertura 1220; lordo 0.03 riaperto correttamente dopo arrotondamento netto 0.02; 2026 input invariato. Registro chiuso alla navigazione iniziale, espandibile con click. Deploy collaudo verificato a0acffde-7d90-4db9-b801-763c204ca37c. Soltanto dati sintetici modificati.

Prossimo passo esatto: verificare deploy main Cloudflare, poi nessun lavoro restante. Non ripetere migrazione o collaudo sul database reale.
