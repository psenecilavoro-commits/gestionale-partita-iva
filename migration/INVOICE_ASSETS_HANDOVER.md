# Importazione beni da fattura — 2026-10-08

Branch main. Checkpoint precedente safety-before-asset-import-2026-10-08, commit 7508df42895db77c4ad272f70befa08aa79267a1.

Implementazione completata: in Carica fattura, per ricevute, selezione Spesa ordinaria / Bene da ammortizzare. Nel secondo caso descrizione, data acquisto, coefficiente e classificazione IVA auto/altro. Non richiede categoria costi, quindi funziona anche per PC/telefono. Intera fattura riferita a un unico bene; non ripartisce fatture miste fra beni e spese. IVA detraibile e coefficiente devono essere verificati dall'utente. Coefficiente tecnico 1 sotto la soglia già usata dal modulo esistente. Nessuna formula Python modificata.

RPC piva_import_invoice estesa con SECURITY INVOKER: stesso salvataggio atomico, duplica zero costi, crea un depreciable_assets acquistato (non simulato) e, nell'ordinario, purchase_vat_invoices; riferimenti nel registro importazioni. Anno del bene secondo data acquisto, distinto da pagamento e periodo IVA. Lock e controlli sui tre anni più anno acquisto. Nessuna policy RLS o permesso esistente cambiato. Migrazione invoice_import_existing_depreciable_assets applicata esclusivamente nel Personale mmkjtvebgtwsjatwifjv.

Verifiche: 47 test JS; 52 Python; compilazione React. SQL transazionale con rollback: regressioni spese ordinarie/emesse, asset senza record costs, asset/IVA/riferimenti, coefficiente invalido, bene piccolo, duplicato, anno chiuso, isolamento RLS e anon. Dati sintetici completamente annullati; verifica test_assets=0, anni rimasti 2026/2027, invoker true, anon_execute false, asset RLS true.

Quote annuali, fondo e residuo sono quelli calcolati da ammortamenti.calcola_bene e quota_ammortamento già presenti, per tutti gli anni successivi. Non aggiunge nuove formule al Conto economico: conserva i collegamenti esistenti.

Prossimo passo: commit/push operativo e conferma deploy Cloudflare. Per controllo visuale aprire una fattura in anteprima, selezionare Bene da ammortizzare e controllare campi/destinazioni, poi Annulla senza registrare dati reali. Il browser CUA risulta non disponibile nella sessione precedente; non dichiarare controllo visuale effettuato.
