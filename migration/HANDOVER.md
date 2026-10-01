# Migrazione React / Cloudflare — checkpoint 2026-10-01

## Ultimo stato verificato — leggere prima

Collaudo Cloudflare pubblicato: https://gestionale-partita-iva-collaudo.pages.dev/ . Progetto Pages separato gestionale-partita-iva-collaudo, deployment 991f691f-3428-457b-9603-8f5798d8fbf7, sorgente d09f661a3804f60aa0ab6d112ea738fbee6c1dd7. Browser remoto verificato: motore locale avviato, Fatturato e Accantonamenti 2026; residuo sintetico 4.271,16 / 4 = 1.067,79. Nessun backend reale collegato.

Diagnosi collegamento Supabase: Plugin Management conferma installed=true, status=ENABLED. Non affermare che sia scollegato. list_projects restituisce ancora Unknown tool supabase.list_projects nella sessione. Tutte le letture tentate falliscono nello stesso modo; non si tratta di un prezzo, né di un errore SQL. Serve ripristinare la disponibilità effettiva degli strumenti prima di creare backend separato o collaudare auth/RLS. Non disinstallare, modificare permessi o chiedere segreti.

Prossimo passo esatto: dalla branch migration/react-cloudflare leggere questa nota, verificare HEAD/stato, tentare una sola lettura Supabase list_projects. Se funziona, verificare org Personale e get_cost per backend staging separato; eventuali costi richiedono conferma. Poi collaudare auth/RLS e mutazioni su soli dati sintetici, completare import PDF/OCR e flussi indicati sotto. Non ripetere backup, setup Cloudflare o implementazione già committata. Produzione non pronta: restano i limiti elencati nella seconda sessione.

## Aggiornamento della seconda sessione — contesto

La migrazione ha ora un frontend React compilabile in web/, con tutte le otto schede rese attraverso un adattatore dichiarativo. Le formule dei 48 moduli Python della baseline sono eseguite localmente con Pyodide/Decimal in un Web Worker; nessun server Streamlit e nessuna riscrittura delle formule. Hash sorgenti in engine-manifest.json. Asset engine.json.gz ricostruibile con migration/build_engine.py.

Il riferimento Ordini effettivamente in produzione NON è main: Cloudflare usa release/produzione-050-prospect, commit 19a7f7122af3ca74f5dc5845ac7ab67d9cd031ab. Ispezionata quella branch in sola lettura: React 18.3.1, Vite 6.4.3, Supabase JS 2.117.2, sidebar responsive e build separate. Il vecchio paragrafo su main più sotto è solo lo stato della prima sessione.

Account Cloudflare verificato: 38e2b19e30fa3cead0657000448218d2. Nessuna modifica a Ordini o ai suoi database. Strumenti Cloudflare ora disponibili e OAuth funzionante.

Validazione eseguita: 50 test originali CPython; 3 test bridge CPython (16 viste, entrambi i regimi, niente errori); 4 test Node (runtime Pyodide su 16 viste, riparto Decimal, isolamento config staging/production, paginazione); build Vite riuscita. Browser locale verificato Fatturato 2026, sidebar con conto economico e Accantonamenti con riparto automatico sui quattro mesi vuoti, usando esclusivamente dati sintetici.

Modalità demo di default: nessuna credenziale, nessun collegamento a Supabase, modifiche solo in memoria e reset ricaricando. Trasporto Supabase predisposto con publishable key, getUser prima delle scritture, JWT utente/RLS esistente, filtri versione, verifica righe restituite e rimappatura ID dei record nuovi. NON ancora collaudato con un Supabase di staging: non abilitare produzione.

Limiti da risolvere: PDF/OCR (pypdf/pypdfium2/PIL/pytesseract originali non ancora adattati al browser); validazione live auth/RLS/concorrenza/mutazioni multiple e flussi completi. Quattro tabelle usate dal codice originale risultano assenti dal database attuale: sales_vat_invoices, vat_periods, pension_payments, purchase_cost_links. In demo sono vuote per collaudare le viste; in produzione non creare nulla e conservare gli errori originali finché non si chiarisce la discrepanza.

Il tool Supabase get_cost ha restituito Unknown tool, non un prezzo: non assumere la disponibilità/costo di branching e non creare risorse a pagamento. Prima del live collaudo serve un backend separato Personale con schema/policy identici e soli dati sintetici. Nessun dato o policy di produzione modificato.

Passo già completato: pubblicare/verificare il progetto Pages distinto gestionale-partita-iva-collaudo dalla branch migration/react-cloudflare con root web, build pnpm build, output dist e modalità demo; poi completare PDF/OCR e il backend di staging. Aggiornare qui URL e commit del deploy quando verificati. Il server preview locale va fermato prima di finire la sessione; nessun lavoro in background.

## Riprendere qui, senza ricominciare

- Repository: psenecilavoro-commits/gestionale-partita-iva.
- Branch di lavoro: migration/react-cloudflare.
- Baseline produzione: a6152b1366fe80cce950bc927a9099e728005cba.
- Backup remoto aggiuntivo: backup-pre-react-2026-10-01, alla baseline.
- Ultimo checkpoint: il commit che contiene questa nota (ottenere con git log -1 sulla branch); non confondere con il commit baseline.
- Nessuna modifica a produzione, formule Python, dati o policy Supabase.
- Test baseline: unittest discover -s tests -q, 50 test superati.

## Backend autorizzato

- Organizzazione Personale: jeekufphnljawewyljsd.
- Progetto gestionale-partita-iva: mmkjtvebgtwsjatwifjv.
- Tutte le 20 tabelle pubbliche hanno RLS attiva. Schema, default e policy completi in supabase-schema-baseline.json. Nessun dato personale incluso.
- Non accedere ai database di Lavoro o Ordini. Solo SELECT di metadati finora.
- Conservare le policy, compresi controlli anno aperto e proprietario; mai service_role nel browser.

## Riferimento Ordini

- Repository psenecilavoro-commits/gestionale-ordini-react, clonato nella directory sorella ordini-reference.
- React 18, Vite 6, lucide-react, sidebar responsive, palette blu, tabelle filtrabili, export ExcelJS, Pages build npm run build, output dist.
- Il README e il codice della versione ispezionata descrivono un prototipo con cinque ordini fittizi e schede segnaposto: non è una baseline di integrazione Supabase collaudata. Riutilizzare pattern visivi/build, NON presumere autenticazione o backend validati.

## Cloudflare setup richiesto in corso

L'utente ha esplicitamente chiesto di eseguire https://developers.cloudflare.com/agent-setup/prompt.md.
Guida letta direttamente. Installate 16 skill ufficiali in C:/Users/pietr/.agents/skills, con copia dal repository ufficiale cloudflare/skills dopo errore installer skills 1.7.0 (yaml mancante). Nessuna skill preesistente sovrascritta.
Registrati i server MCP cloudflare, cloudflare-docs, cloudflare-bindings, cloudflare-builds e cloudflare-observability nella configurazione Codex globale. OAuth completato per tutti e quattro i server privati; il server documentazione è pubblico. Verificare disponibilità strumenti dopo riavvio. CLI cf opzionale non installata.
L'autorizzazione OAuth è completata. L'utente deve riavviare Codex per caricare gli strumenti. Nessun account/progetto Pages ancora verificato.

## Lavoro rimanente

1. Dopo autenticazione/riavvio, verificare strumenti Cloudflare e identificare progetto Pages Ordini in sola lettura.
2. Riprendere la branch migration/react-cloudflare, leggere questa nota e schema, verificare HEAD e stato pulito. Non riclonare né ripetere setup/backup.
3. Completare inventario funzioni/operazioni e matrice parità per tutte le schede Python attuali, distinguendo dati reali, stime, esempi e parametri provvisori.
4. Scegliere preservazione esatta Decimal e generare fixture oracle Python con casi soglia, anni e dati sintetici. Vietato semplificare calcoli o convertire indiscriminatamente in float.
5. Implementare React, autenticazione Supabase con chiave pubblica, cancellazione dati su logout/cambio anno e paginazione. Nessuna scrittura collaudo al backend di produzione.
6. Implementare integralmente 2026 forfettario / 2027+ ordinario, sidebar e conto economico, accantonamenti e residuo, chiusura/riapertura, IVA, costi/auto, imposte, detrazioni/deduzioni, ammortamenti, import XML e registri presenti.
7. Ambiente di collaudo isolato con dati sintetici e stesso schema/policy; valutare eventuali costi prima di creare progetti o branch Supabase. Non cambiare il backend Personale di produzione.
8. Build, test automatici parità/security e collaudo funzionale browser, poi deploy preview Cloudflare distinto da produzione. Migrazione ancora NON implementata e nessun ambiente di collaudo pronto.

## Regole di continuità

Salvare commit + aggiornare nota prima di interruzioni. Nessun lavoro in background fuori sessione; non aspettare ricariche. I file sources della directory progetto restano read-only. L'utente vuole comunicazioni solo per interventi necessari o collaudo pronto.


