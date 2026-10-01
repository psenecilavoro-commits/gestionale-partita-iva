# Migrazione React / Cloudflare — checkpoint 2026-10-01

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

