# Stato della struttura — 21 settembre 2026

La struttura applicativa delle sette sezioni è completata nel ramo di consegna. Non equivale a validazione fiscale, applicazione delle migrazioni o collaudo del Supabase reale. Nessuna personalizzazione grafica introdotta: le modifiche estetiche saranno guidate dall’utente nella chat originale, poi seguirà il controllo delle funzioni.

## Sezioni e collegamenti

| Sezione | Struttura disponibile |
| --- | --- |
| Fatturato | Mandanti, mesi, zeri distinti dai vuoti, proiezioni; registro separato IVA vendite/fatture/note di credito con CRUD ed export |
| Costi | Stime annuali distinte dalle spese documentate; inserimento e modifica delle spese di tutte le categorie previste; collegamento uno a uno fra costo e fattura acquisto senza duplicare importi |
| Auto | Veicoli reali, percorrenze mensili reali, dati di prova separati, carburante, autostrada, rate e limiti |
| Accantonamenti | Provvigioni nette manuali, riserve, importazione assistita, quadro mensile, acquisti IVA; prospetti mensili/trimestrali con completezza dichiarata, credito iniziale, rettifiche, interessi e versamenti separati |
| Conto economico | Riproduzione letterale del foglio separata dallo scenario sulle registrazioni; INPS per anno di pagamento, Enasarco distinto, pensione versata e limite esplicito di scenario |
| Imposte | Parametri provvisori, confronti Enasarco/INPS/IRPEF e registro contributi documentati |
| Detrazioni e deduzioni | Sanitarie unificate, rate pluriennali, deduzioni manuali; registro separato versamenti fondo pensione |

## Vincoli conservati

- Fatturato integrale: Enasarco non ne modifica il valore. Le provvigioni nette restano un input manuale distinto.
- I contributi INPS di competenza precedente sono un sottoinsieme del versato nell’anno: non vengono sottratti due volte.
- Stime INPS e fondo pensione di prova non diventano pagamenti. Le note di credito hanno importi positivi in archivio e segno negativo applicato una volta nel prospetto IVA.
- Le spese non vengono ricreate dall’importazione IVA. Il collegamento documentale non modifica costi, fatturato o provvigioni.
- Nessun caricamento automatico di dati di prova all’apertura. Nessuna modifica remota ai dati esistenti è stata eseguita da questa attività.
- Google Sheets originale letto soltanto in lettura il 21/09/2026. Formule e risultati di riferimento in `tests/formule_foglio.json`; non è un archivio di pagamenti reali.
- Ripristinata la sottrazione di H18 (avanzo A.P.) in Tabella accantonamenti!E16. Le formule del foglio non sono state corrette tacitamente per ragioni fiscali.

## Robustezza e verifiche

- Paginazione dei registri principali (anche oltre 1.000 righe), blocco duplicati/anomalie nel fatturato e validazione importi finiti.
- Pulizia della sessione al logout e dei moduli al cambio anno; rifiuto chiavi service_role/secret.
- Nuove tabelle: RLS per proprietario dell’anno, scritture solo in anno aperto, vincoli duplicati e versioni per evitare sovrascritture concorrenti.
- Tabelle nuove assenti: messaggio di prerequisito, nessuna scrittura di ripiego nelle vecchie tabelle.
- Dipendenze dirette fissate e snapshot `requirements-lock.txt` dell’ambiente verificato; rimosso l’argomento Streamlit deprecato `use_container_width` mantenendo la stessa larghezza.
- Suite locale: unittest con formule, import XML, documenti IVA, cassa, paginazione, sicurezza sessione e AppTest. Esito effettivo e CI riportati nel documento di consegna.
- CI: test Python e test SQL su PostgreSQL temporaneo con schema minimo di contratto, senza credenziali Supabase.

## Prerequisiti non applicati

1. Progetto Supabase **Partita IVA**, secondo account: resta l’unica destinazione autorizzata. Ordini e Prospect non sono stati interrogati o modificati.
2. Verificare backup, schema base e RLS esistenti. Lo schema base non è versionato integralmente in questo repository.
3. `SQL_PROVVIGIONI_NETTE.sql` e `SQL_IVA_ACQUISTI.sql` devono già essere presenti nel progetto corretto.
4. Eseguire `SQL_COMPLETAMENTO_STRUTTURA.sql` soltanto lì, dopo controllo manuale dell’URL/ref del progetto e della guardia in testa. È transazionale e rieseguibile; non migra né cancella dati preesistenti. **Non applicato al Supabase reale.**
5. Collaudare RLS con utenti A/B/anon e flussi completi nello schema reale: i test del database temporaneo non lo sostituiscono.

## Limiti funzionali deliberati per la fase di controllo

- Tutti i parametri fiscali 2027 restano scenari non verificati. Nessun versamento o dichiarazione viene prodotto automaticamente.
- Prospetti IVA: importi documentali e rettifiche manuali, nessun automatismo di scadenze, interessi, riporto credito, regimi speciali, reverse charge o note di credito acquisti. La casistica speciale va verificata e rappresentata con rettifiche confermate.
- Fatturato e imponibile del registro vendite non si sincronizzano: richiedono riconciliazione, anche per note di credito e differenze di periodo.
- Contributi: registrazioni dichiarate/documentate, non attestazioni dell’ente. Deducibilità da verificare.
- Scenario a cassa: costi deducibili confermati manualmente; deduzioni generiche e detrazioni personali mostrate nei propri registri, non applicate automaticamente alle imposte. Il calcolo non determina il netto finanziario.
- Fondo pensione: limite manuale di scenario, nessun limite 2027 inventato. I vecchi pagamenti nelle deduzioni generiche non vengono riclassificati né duplicati automaticamente.
- Collegamenti acquisti/costi uno a uno; ripartizioni su più costi restano verifica manuale. Nessuna conservazione dei file originali.
- Le garanzie RLS e concorrenza del vecchio schema richiedono verifica sul progetto corretto; questo lotto non riscrive le policy legacy senza conoscerne lo stato.
- OCR/Tesseract, documenti reali, distribuzione Streamlit e database remoto restano da collaudare. I test AppTest usano un client finto.

Vedere `HANDOVER_STRUTTURA.md` per esecuzione, test e prossima fase.

## Compatibilità con il nuovo commit su main

Integrato il commit b916a65 (SQL_IVA_VENDITE.sql), comparso durante il lavoro. Il registro vendite mantiene principal_id e le policy di proprietà della mandante. Il nuovo SQL aggiunge soltanto version e vat_month quando assenti: il mese dei documenti preesistenti resta NULL e deve essere confermato, senza riclassificare automaticamente dati storici. Il prospetto IVA resta sospeso finché i mesi mancanti non sono confermati. La CI verifica anche questo percorso e la conservazione degli importi legacy.
