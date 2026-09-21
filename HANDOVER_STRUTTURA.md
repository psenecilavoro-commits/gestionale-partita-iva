# Handover della strutturazione

## Consegna

Modifiche coordinate su un ramo dedicato. Nessuna modifica grafica personalizzata, nessun accesso al connettore Supabase e nessuna scrittura al foglio Google. L'app mantiene sette schede; i moduli documentali nuovi usano componenti standard.

Il riferimento letto è [calcoli partita iva pietro 2027](https://docs.google.com/spreadsheets/d/1-FsiHFWzuEWmRbASdeSrowjIE73U5-GanDJkn5tEzAE/edit), tutte e sette le schede entro i limiti effettivi. La fixture contiene formule e risultati di prova, non una validazione delle norme 2027.

## Moduli nuovi

- `registri.py`: paginazione, controllo anno aperto, importi e scritture con versione sulle tabelle nuove.
- `struttura_calcoli.py`: calcoli puri IVA documentale e variante a cassa; validazioni.
- `struttura_ui.py`: vendite, periodi IVA, pensione, scenario a cassa e riconciliazione costi/acquisti.
- `registrazioni_reali.py`: veicoli/percorrenza effettivi e spese documentate non auto; categorie auto gestite dai moduli esistenti.
- `SQL_COMPLETAMENTO_STRUTTURA.sql`: tre tabelle aggiuntive ed estensione compatibile del registro vendite, indici, vincoli, RLS, controllo anno/proprietario e versioni. Nessuna alterazione dei dati legacy.

## Test e limiti delle prove

Ambiente locale Windows, Python 3.12, Streamlit 1.64.0 e Supabase Python 2.31.0. Esito locale del 21/09/2026: **29 test unittest/AppTest superati**, compileall senza errori, pip check senza dipendenze incompatibili e git diff --check superato. I client AppTest sono finti: nessuna rete e nessuna credenziale reale.

I test di regressione confrontano tutte le celle numeriche prodotte dal Conto economico con la fixture del foglio, arrotondando soltanto alla presentazione. Ulteriori casi: mesi vuoti/zero/duplicati, Enasarco distinto, H18, contributi A.P. per cassa, fondo limitato, perdita senza imposta negativa nella variante, IVA note di credito, periodi sovrapposti, date future, XML non sicuri, CSV, paginazione oltre 1.000 righe, logout/cambio anno e chiavi privilegiate.

La CI aggiunge PostgreSQL 17 temporaneo: schema minimo di contratto, doppia applicazione SQL, guardia progetto, isolamento A/B/anon, anno chiuso, versioni e vincoli. **Esecuzione remota superata** sul commit c828d25: [workflow PR](https://github.com/psenecilavoro-commits/gestionale-partita-iva/actions/runs/35620740302), incluso lo step SQL. Locale: PostgreSQL/psql/Docker non disponibili, quindi il test SQL è stato eseguito in CI, non localmente. Questo non attesta lo schema Supabase reale.

## Attivazione nel progetto corretto

1. Verificare la PR e il workflow; effettuare backup del solo progetto Partita IVA del secondo account.
2. Controllare lo schema base e le RLS esistenti. Prerequisiti: fiscal_years con id/user_id/fiscal_year/status; costs e purchase_vat_invoices con id/fiscal_year_id; le altre tabelle già usate dall'app.
3. Verificare gli script provvigioni nette e IVA acquisti già presenti. Non eseguire SQL su Ordini/Prospect.
4. Controllare manualmente nome e URL/ref del progetto nel SQL Editor. Nel nuovo script sostituire soltanto `DA_CONFERMARE` con `CONFERMO_SOLO_PARTITA_IVA`, poi eseguire l'intera transazione. La guardia evita l'esecuzione accidentale del file invariato, ma non identifica autonomamente l'account/progetto: tale verifica resta necessaria.
5. RLS: provare con utenti A/B e anonimo ogni nuova tabella, inclusi inserimenti con anno altrui, collegamenti a costi altrui, modifiche/eliminazioni in anno chiuso e due aggiornamenti con la stessa versione.
6. Verificare sullo schema reale vincoli univoci e chiavi esterne legacy; non sostituire policy esistenti alla cieca. Provare due prospetti IVA sovrapposti anche in concorrenza.
7. Distribuire il ramo approvato su Streamlit, aggiornare dipendenze e verificare login e sette schede. Nessuna chiave server privilegiata.

**Il nuovo SQL non è stato applicato al Supabase reale.** Non sono state verificate le credenziali, le policy attuali, l'OCR di documenti reali o la distribuzione Streamlit.

## Ripresa nella chat originale

L'utente vuole tornare a “Gestionale partita iva 3” per guidare le modifiche grafiche e funzionali. Partire da questa consegna e da `STATO_STRUTTURA.md`, senza azzerare o ricaricare dati di prova sui dati esistenti. La successiva fase di controllo dovrà verificare formule, documenti, ammissibilità/limiti fiscali e norme 2027: non è già completata.

Non dedurre dal fatturato l'Enasarco; non ricavare automaticamente le provvigioni nette; non trattare l'assenza di registrazioni come zero confermato; non equiparare il netto del foglio a disponibilità di cassa. Il nuovo scenario non applica automaticamente detrazioni o deduzioni generiche e richiede la quota deducibile dei costi confermata dall'utente.

Documentazione tecnica consultata: [RLS Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security), [paginazione Python](https://supabase.com/docs/reference/python/range), changelog Supabase e documentazione Streamlit inclusa nel pacchetto installato. Nessuna affermazione di verifica fiscale definitiva.

## Compatibilità con il nuovo commit su main

Integrato il commit b916a65 (SQL_IVA_VENDITE.sql), comparso durante il lavoro. Il registro vendite mantiene principal_id e le policy di proprietà della mandante. Il nuovo SQL aggiunge soltanto version e vat_month quando assenti: il mese dei documenti preesistenti resta NULL e deve essere confermato, senza riclassificare automaticamente dati storici. Il prospetto IVA resta sospeso finché i mesi mancanti non sono confermati. La CI verifica anche questo percorso e la conservazione degli importi legacy.
