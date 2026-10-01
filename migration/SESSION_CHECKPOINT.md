# Checkpoint pronto per riprendere — 2026-10-01

Branch: `migration/react-cloudflare`. Ultimo commit applicativo verificato: `16cb54612c03ec6917b4933a1eeeef1e3c080e8d`. PR bozza: https://github.com/psenecilavoro-commits/gestionale-partita-iva/pull/13 . Leggere il HEAD della branch per il commit di questa nota.

Completato: React/Cloudflare isolato, grafica, autenticazione e Supabase gratuito di collaudo; formule originali preservate; confronti CPython/Pyodide di metriche/tabelle/CSV per 16 viste; PDF/XML/OCR locali e conferme; salvataggi e isolamento utenti per costi, percorrenza, ammortamenti, detrazioni/deduzioni, IVA e pensione; chiusura/riapertura. Corretto il reset dei moduli clear_on_submit e verificato nel browser: bene previsto1000/coeff20 con quota100, poi descrizione/importo vuoti e conferma disattivata. Tutti i record temporanei manuali e automatici rimossi; 2026 open.

Verifiche riuscite sul commit applicativo: entrambe CI, quattro test bridge, cinque test Node e build; deploy `64c1b38d-dd1d-4d23-a3bd-ce628a2bd725` riuscito. I 48 moduli fiscali root sono identici alla baseline `a6152b1366fe80cce950bc927a9099e728005cba`.

Produzione NON modificata. Backend Personale originale `mmkjtvebgtwsjatwifjv`: 20 tabelle e 82 policy confermate. Piano per quattro registri mancanti in PRODUCTION_PLAN.md e fotografia in production-preflight.json. Nessun progetto Lavoro o database Ordini coinvolto.

Prossimo passo esatto: acquisire la risposta alla domanda asincrona già inviata: nel collaudo, scheda Costi, «Esporta spese registrate CSV» scarica effettivamente il file? Il browser automatico non riceve download né con waitForEvent né con downloadMedia; payload CSV e nome sono verificati, ma NON assumere il download riuscito. Il link nativo è pubblicato. La scheda utente1 è stata lasciata in Costi. Se riuscito, proseguire con preflight aggiornato e passaggio in produzione secondo PRODUCTION_PLAN.md; se fallisce, correggere l’esportazione prima della produzione.

Nessun processo locale o lavoro fuori sessione. Credenziali sintetiche solo nel file ignorato web/.staging-test-users.json. Non ricreare progetto, non rieseguire seed, non ripartire dalla baseline. Handover storico in HANDOVER.md.
