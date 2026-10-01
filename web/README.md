# Gestionale Partita IVA React — collaudo isolato

React 18 + Vite, sidebar responsive ispirata alla release effettivamente pubblicata del Gestionale Ordini. Il motore fiscale è lo stesso codice Python, eseguito in un Web Worker con Pyodide, Decimal originale e nessun server Streamlit. I 48 moduli della baseline sono conservati integralmente e verificabili in migration/engine-manifest.json.

Modalità predefinita: demo. I dati sintetici vivono soltanto in memoria e vengono ripristinati ricaricando la pagina. Nessuna connessione al Supabase reale.

Build: pnpm install --frozen-lockfile, pnpm build. Test: pnpm test. Cloudflare Pages: root web, build pnpm build, output dist. I sorgenti Python vengono inclusi nell'asset engine.json.gz, generato da migration/build_engine.py. La compilazione non riscrive le formule.

Configurazione dati reali: VITE_APP_MODE=production, VITE_SUPABASE_URL del progetto Personale mmkjtvebgtwsjatwifjv, VITE_SUPABASE_PUBLISHABLE_KEY. Il frontend rifiuta altri backend in produzione e rifiuta il backend di produzione in staging. Nessuna chiave privilegiata. Le richieste usano il JWT utente e le policy RLS esistenti.

## Validazione ancora necessaria prima della produzione

- Supabase separato di staging: login/logout, policy cross-user, anno chiuso, errori e concorrenza su dati sintetici.
- Import documenti: XML disponibile; librerie PDF e OCR native della versione Python non sono ancora incluse nel runtime browser. Non dichiarare parità degli import PDF/JPG/PNG.
- Completare il collaudo delle operazioni di inserimento/modifica/eliminazione di tutte le schede; verificare anche le operazioni che inseriscono più record collegati.
- Il backend attuale ha 20 tabelle pubbliche. Le funzioni originarie riferiscono inoltre sales_vat_invoices, vat_periods, pension_payments e purchase_cost_links, assenti dalla fotografia corrente: conservare il comportamento originale di errore, non creare queste tabelle in produzione né alterare RLS senza risolvere la discrepanza.
- Nessun deploy di produzione è autorizzabile come migrazione completa finché queste verifiche non sono superate.
