# Carica fattura — 2026-10-08

Branch operativo: main. Checkpoint precedente: safety-before-invoice-import-2026-10-08 (ae6cd991).

La nuova scheda React è separata nella sidebar e non dipende dall'anno visualizzato. Lettura XML TD01 con namespace, PDF/immagini assistiti attraverso il motore locale esistente. Il file non viene conservato. Anteprima modificabile, categorie suggerite, date economiche e IVA separate, conferma esplicita. Zero registrazioni prima della conferma.

`invoice-import.sql` aggiunge solo il registro invoice_imports con RLS proprietario e una RPC SECURITY INVOKER. Politiche esistenti invariate. Scritture in unica transazione, blocco anni chiusi con lock per anno e row lock, controllo stale del totale mensile, chiave documento e vincoli dei registri per duplicati. Costi misti vengono divisi per riepilogo IVA mantenendo una categoria; riferimenti memorizzati nel registro importazioni. Fatture emesse incrementano il netto del mese dell'incasso e registrano IVA nel mese emissione.

Limiti deliberati: fatture TD01, integralmente pagate/incassate; categorie devono essere configurate per l'anno di pagamento; PC/telefono, penali, note credito, bollo/cassa/sconti e casi IVA speciali restano nei moduli completi. Il cambio forfettario/ordinario attraversato dall'incasso di una fattura emessa richiede registrazione manuale verificata. IVA acquisti nel mese registrazione, nessuna anticipazione automatica. PDF richiedono verifica/correzione degli importi e del soggetto. Non considera tutta l'IVA detraibile senza conferma. Categorie e formule ordinarie provvisorie non vengono dichiarate validate: i prospetti originali possono segnalare incompleto per righe con parametri diversi dalla categoria (es. IVA mista leasing); non si forza una stima fiscale.

Verifiche: 43 test JS passati inizialmente (10 nuovi per XML, PDF, date, anno chiuso, duplicati, imposte miste, zero modifiche in anteprima, aggregati e due regimi); compilazione React passata. SQL collaudato nel progetto Personale con transazione interamente annullata, incluse tutte le fixtures: IVA mista, inserimenti collegati, duplicati, aumento fatturato, stale, totali invalidi e anno chiuso.

Browser: due inizializzazioni CUA fallite con "trusted Node process exited unexpectedly". Non dichiarare collaudo visuale eseguito. Non sono state salvate fatture reali.

Implementazione: commit 85a05a38c62f5ff366b1e8491983210c7e67be06 su main. Migrazione e test sicurezza completati; pubblicazione Cloudflare avviata. Prossimo passo esatto per il collaudo visivo: aprire Carica fattura, selezionare il PDF di esempio o un XML TD01, controllare voci/date/destinazioni senza premere Conferma importazione, poi Annulla. Gli strumenti browser di questa sessione non consentono di completare questa verifica.

Migrazione invoice_import_atomic_preview applicata nel solo progetto Personale mmkjtvebgtwsjatwifjv. Registro vuoto, RLS attiva, RPC invoker e anon non autorizzato verificati. Test: 43 JavaScript, 52 Python, SQL rollback inclusi isolamento e anon. Advisor senza segnalazioni sulle nuove risorse; preesistenti rls_auto_enable eseguibile e protezione password compromesse disattivata, non modificati. Resta verifica visiva browser (strumenti non accessibili), usare documento senza confermare salvataggio.
