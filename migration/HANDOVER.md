# Salvataggi e fedelta dei moduli - 2026-10-01
Commit download aa2b826efccd00b476e59aa16d6de83ece6013f0 pubblicato, deploy68f1f85a riuscito, entrambeCIpassate. Costi UI inserito13.50/modificato14.50 e rimosso record COLLAUDO REACT TEMP20261001; percorrenza1234->1300 e ripristino; bene previsto2027 1000/coeff20 con quota100 verificato e rimosso. Test esplicito web/tests/staging-write-roundtrip.mjs PASS per CRUD+isolamento secondo utente su costs, vehicle_monthly, depreciable_assets, tax_credits, tax_deductions; tutti record automatici rimossi, logout solo locale per non revocare sessione browser.
Rilevato clear_on_submit ignorato dall'adattatore: corretto senza cambiare i moduli fiscali. Dopo submit ripristina default e conferme dei soli widget del form; dopo scrittura confermata React usa next.inputs prima del render successivo. Test reale bene previsto/payload/reset PASS,4testbridge. CIstruttura include ora testbridge.
Download nativo ancora non verificabile dal controllo browser: waitForEvent e downloadMedia scadono senza consoleerror, link osservabile spese_2026.csv. Chiesto all'utente in domanda asincrona di provarlo nella scheda Costi; attendere risposta, non assumere esito positivo. La scheda utente1 resta in Costi; scheda test2 temporanea. Nessun processo locale.
Produzione solo letta: refmmkjtvebgtwsjatwifjv, orgPersonalejeekufphnljawewyljsd,20tabelle/82policy confermate, funzione completamentoassente. Fotografia production-preflight.json e piano PRODUCTION_PLAN.md; nessun progetto Lavoro accesso, nessun dato reale modificato. Prossimo passo esatto: pubblicare e verificare resetform, confermare assenza residui sintetici, acquisire esito download; poi completare4registri e Pagesproduzione secondo piano. Non riseminare.

# Ripresa download e scritture - 2026-10-01
Ripresa da5e112291a36f5c46669af94ccd983edf05435a7e, PRbozza13 allegata. CI entrambe passate (React migration parity e Verifica struttura con PostgreSQL temporaneo). Deploy4a2bb22e-c7dd-4cc7-93a0-ccbfb883fc9c riuscito. Correzione download in main.jsx: link nativo con hrefBlob e attributo download, cleanup URL in effect; payload CSV fiscale invariato. Build locale passata. Da verificare nel browser dopo deploy. In corso collaudo spesa sintetica COLLAUDO REACT TEMP 20261001 importo13.50 nel2026: verificare creazione e rimuovere solo questa registrazione a fine prova. Backend solo staging gbtvscldenpmvcvwognw. Nessun cambiamento produzione.
Prossimo passo esatto: verificare download nativo e costo sintetico, poi Auto/detrazioni/ammortamenti, piano4tabelle mancanti produzione. Non riseminare dati; usare credenziali locali ignorate. Branch migration/react-cloudflare.

# Verifica pubblicazione e CSV - 2026-10-01
Ultimo checkpoint sorgente bfa115d930a9c84c225141d43081ea4e34b9741c. Deploy724f01c6-9b92-4bb3-82b2-7a880746b15f riuscito. Deploy precedente23c9792a fallito per socket di rete durante bootstrap pnpm, prima del build del progetto. Confronto CPython/Pyodide esteso ai payload e nomi/MIME delle esportazioni CSV. Browser IAB: click esportazione senza errori console ma evento download non consegnato entro10s, scaricamento effettivo ancora da verificare in browser. Non dichiarare CSV browser collaudato. Prossimo passo: verifica CSV, collaudo restante scritture e piano4registri mancanti in produzione; non applicare produzione per sola parita16viste. Produzione e SupabaseLavoro intatti.

# Parita fiscale CPython/Pyodide - 2026-10-01
Confronto automatico passato per tutte le metriche e tabelle delle8schede x2anni2026/2027, usando risultati CPython delle formule originali come riferimento; oracle sintetico web/tests/fixtures/fiscal-parity.json generato da migration/generate_parity.py. 48moduli originali verificati contro a6152b1366fe80cce950bc927a9099e728005cba, invariati. Test5Node passati inclusa parita16viste. CI corretta: build prima dei test, per creare lettori wheel locali necessari ai nuovi test documentali. Prossimo passo: verificare CI/deploy di questo checkpoint, audit delle scritture/CSV e piano dei4registri mancanti in produzione. Produzione ancora NON modificata; nessun processo locale in background.

# Collaudo documenti verificato - 2026-10-01
Sorgente documenti: 02e184bdf86a9fc445463bedf62a7dbf1e081f85. Deploy39dbab9b-2711-4201-a94e-b85727291ba5 riuscito. Browser remoto: PDF fattura1234.56, immagine OCR1234.56, PDF scansionato OCR1234.56, XML123.45 e PDF sanitario123.45 letti. PDF oltre4pagine passa al manuale. Salvataggio fattura2027 confermato1234.56 e ripristinato3900; sanitario123.45 confermato nel DB e stesso file segnalato duplicato senza ricontarlo; record sanitario sintetico eliminato dopo test. Nessuna produzione modificata. Test5Node e build passati, 48moduli fiscali intatti. Corretto messaggio sanitario: lettura nel browser. Server localhost fermato; suo errore fetch non presente su Cloudflare.
Prossimo passo: completare audit dei flussi di scrittura/CSV e parita originale, preparare piano dei4registri mancanti in produzione prima del passaggio finale. NON rieseguire seed. Riprendere dalla branch migration/react-cloudflare, non dalla baseline. Credenziali sintetiche solo nel file ignorato. Nessun processo in background.

# Checkpoint documenti — 2026-10-01
Branch: migration/react-cloudflare. Precedente checkpoint: 8e344e3501413004ffe3e56c32c0c8d0c7bff48d.
Implementati lettori PDF/XML originali con pypdf 6.19.0 e defusedxml 0.7.1, OCR locale Tesseract 7, rendering PDF.js 6.3.289, asset self-hosted con checksum. Nessuna modifica ai 48 moduli fiscali originali, nessun file inviato a servizi esterni. Test originali 50, bridge 3, Node 5 passati; build passata. Import documenti ancora DA COLLAUDARE nel browser: preview localhost avvia UI ma restituisce TypeError Failed to fetch senza console errors; risorse HTTP verificate 200. Aggiunta diagnostica per runtime/wheel/formule. Prossimo passo esatto: verificare questa build nel collaudo Cloudflare e provare invoice.pdf, invoice.png e medical.pdf; riconciliare importazione/conferma/manual fallback e duplicati. Poi collaudo completo delle scritture e parità funzionale. Produzione NON modificata. Quattro tabelle presenti solo nel collaudo richiedono piano prima della produzione. Credenziali sintetiche restano nel file ignorato web/.staging-test-users.json. Non riseminare database.
# Migrazione React / Cloudflare — checkpoint 2026-10-01

## Esito grafica finale
Correzione9dbdd037518fa1a5ca17ed43bb8c353a0274cd70 pubblicata (eb7ac3b2-be10-461c-83a4-1a0fb8765fe8). Browser reload+navigazione Accantonamenti verificati senza alert; screenshot finale con tutti i comandi abilitati e importi invariati. Layout390px menu con backdrop/chiusura verificato; viewport ripristinato. Quattro test Node passati. Nessun processo locale in background. Prossimo passo PDF/OCR e parità integrale, mantenendo collaudo gratuito.
## Verifica grafica e correzione avvio
Deploy grafica e60c5c22d6fc9b57f42aee3bc73d23f49b83f70b riuscito:8d208288-d23f-4c01-9c31-6d9fcfb81b02. Desktop e menu390px verificati. Rilevato errore intermittente NameError react_bridge dopo avvio: messaggi worker concorrenti eseguivano render prima di completare init. Corretto con una promessa di inizializzazione condivisa e coda seriale di richieste. Verificare nuovo deploy con reload e navigazione prima del prossimo passo PDF/OCR. Nessun cambiamento formule.
## Grafica richiesta dall’utente
Utente autorizza prosecuzione autonoma e chiede stile come Ordini. Riferimento UI letto da release/produzione-050-prospect 19a7f712. Main.jsx: icone navigazione, intestazione sezione, badge collaudo, menu mobile con chiusura e backdrop, Markdown sicuro come elementi React (nessun HTML iniettato). CSS: palette azzurra, pannelli e metriche con bordi/ombre leggeri, tabelle ordinate, sidebar sticky scorrevole e layout mobile. Build passata. Formule, backend e dati intatti.
Prossimo passo: verificare deploy e resa desktop/mobile, poi riprendere PDF/OCR e parità finale. Non migrare produzione prima di completare i punti aperti.
## Verifica successiva
Browser remoto: tutte8schede x 2026/2027 =16viste verificate senza alert dopo completamento struttura staging. Utente test0 autenticato nel tab consegnabile. Fatturato Gennaio ripristinato4500; anno2026 open. Password test nel file locale ignorato, non riutilizzare credenziali produzione.
Deploy ce1c948b777b50f10c669363975fb925744246fc riuscito: 225c0bd4-0397-44ec-b910-747bf0875203. Test Auth/RLS ripetuto su dati popolati, PASS anche registrazione IVA vendite, isolamento secondo utente, update con version1->2, rifiuto update stale version1, rifiuto update anno chiuso, registrazione pensione e rifiuto periodi IVA sovrapposti. Record temporanei test eliminati, anno2026 riaperto. Nessuna operazione produzione.
## Collaudo live verificato e completamento struttura — contesto
Deploy live Auth verificato 008c7ba4-e8e2-40fb-99b7-564510bfe103, sorgente 66e80bef086ad6b72758ce9caf426d0fc6cb0d6e. Browser login utente sintetico 0 riuscito; fatturato Gennaio 2026 modificato 4500->4600, confermato via SELECT staging, poi ripristinato4500; chiusura anno verificata sia DB sia UI sola lettura, riapertura riuscita.
Le viste 2027 hanno mostrato errori sui 4 registri mancanti. Trovato SQL_COMPLETAMENTO_STRUTTURA.sql nella baseline, esplicitamente NON APPLICATO. Applicato SOLO su staging (gbtvscldenpmvcvwognw), sostituendo soltanto il flag conferma dopo verifica ref. Migration staging_validate_existing_structure_script crea 4 tabelle e relative policy/trigger già previste dallo script originale; non cambia le 82 policy delle 20 tabelle base. Lo staging ora ha24tabelle. Main.jsx carica le4 aggiuntive SOLO in modalità staging; produzione continua a leggere solo baseline20.
Prossimo passo immediato: verificare deploy di questo checkpoint e tutte16viste. Registri nuovi ancora vuoti; collaudare insert/update/version/periodi con date lecite (anno2027 futuro rispetto alla data corrente). Produzione resta senza4registri: decisione/schema necessaria prima del passaggio finale, nessuno script applicato al progetto originale. PDF/OCR ancora da completare.
## Sessione collaudo gratuito — contesto precedente
Supabase riconnesso: usare link_id link_6abe5d9a48cc81919d5364d1ffb82d7c (Primary, organizzazione Personale). L'altro collegamento è Lavoro: non usarlo.
Utente ha autorizzato progetto separato GRATUITO. get_cost project ha restituito 0/mese, confermato; creato gestionale-partita-iva-collaudo, ref gbtvscldenpmvcvwognw, eu-west-1, ACTIVE_HEALTHY. NON creata branch Supabase a pagamento.
Applicata migration personale_schema_staging_clone: 20 tabelle, 160 constraint, 82 policy identiche alla baseline, due funzioni piva e trigger originali. SQL in staging-schema.sql, colonne in staging-columns.json. Produzione letta solo per metadati. Nessun dato reale copiato.
Due utenti artificiali di test creati nel solo nuovo progetto. Credenziali random locali in web/.staging-test-users.json, ignorate da Git. Non committare/pubblicare password. Dati sintetici demo-owner copiati all'utente test 0 con UUID nuovi; unit EUR nelle fixture dei parametri (nessuna formula modificata); solo 20 tabelle esistenti, nessuna delle 4 mancanti creata.
Verifiche PASS: SQL ruolo authenticated isolamento SELECT/INSERT, identità anno immutabile, close/reopen. Node tests/staging-live.mjs: reale Auth password/JWT/getUser, isolamento utenti, insert cross-owner negato, close/reopen dal trasporto, anon senza dati, logout. Quattro test Node base e build passati. Seed-staging.mjs è UNA TANTUM, non rieseguirlo su DB già popolato.
Cloudflare Pages collaudo configurato staging con nuova URL e chiave publishable; demo precedente sostituita al prossimo deploy. Nessuna chiave privilegiata. In main.jsx corretti limite spread file grandi e busy al cambio sessione; banner esplicito staging.
AVVISO PARITÀ: RLS originale di monthly_reserves è owner-only, senza guardia anno chiuso; preservata identica. Il blocco UI dell'anno chiuso va collaudato; non attribuire al database protezioni assenti e non cambiarle senza richiesta. Quattro tabelle IVA/pensione citate sotto ancora assenti anche in staging; preservati errori originali.
Prossimo passo: verificare deploy del checkpoint su gestionale-partita-iva-collaudo.pages.dev, login con utente sintetico locale, tutte le 16 viste e flussi scrittura, anno chiuso/riaperto UI; completare PDF/OCR e controlli concorrenza/mutazioni prima di produzione. Mai ricreare progetto o ripetere seed. Stato migrazione ancora incompleto.

## Stato sessione precedente — contesto

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




