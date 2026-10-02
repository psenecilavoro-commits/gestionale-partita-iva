# Modifica diretta Fatturato — 2026-10-02

Autorizzata dall’utente per tutte le mandanti, esclusivamente scheda Fatturato. Celle mensili, incluse mancanti, aprono finestra con mandante/mese/anno e importo IVA esclusa. Salva sostituisce via modulo Python originale; Annulla non modifica i dati. Zero distinto da assenza; totali, medie, stime e altre schede rimangono non modificabili.

Nessuna formula fiscale originale modificata, nessuna scrittura di prova in produzione, nessuna modifica Supabase/RLS. Controllo anno aperto riletto prima di salvare; confronto con record all’apertura e filtro atomico sul precedente importo per aggiornamenti concorrenti. Dialogo chiuso su logout e pagina sottostante inert; Esc annulla.

Test:5 bridge/6 Node, build; CI precedenti4b6ff3a entrambe passate. Browser demo Cloudflare verificato:4500 sostituito con123,45, riepiloghi aggiornati; Settembre vuoto salvato0 e mesi compilati8->9; Dicembre99 annullato rimane vuoto; anno2026 chiuso disabilita tutte le celle. Collaudo configurato DEMO senza URL/chiave Supabase, nessun secondo progetto ricreato. Ultimo commit applicativo fb9d7d80524d2b566e7e6bb46cc04a56fd5a1769. PR15; completare CI/deploy di questo HEAD prima del merge. Il vecchio modulo di inserimento rimane disponibile.

Nessun processo locale o lavoro fuori sessione. Per prossime schede concordare separatamente con l’utente quali dati sono manuali e quali derivati. Non estendere automaticamente il metodo.
