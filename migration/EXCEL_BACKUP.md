# Backup Excel — checkpoint 2026-10-03

Implementato e integrato tramite PR #20. Branch feature/backup-excel, ultimo commit funzionale 425559e3941de165d53850411a83ab9f4b533bef.

Pulsante nella riga Esci solo in Fatturato. ExcelJS lazy load, elaborazione locale; export prospetti otto schede dell’anno selezionato col motore Python esistente, risultati fissati e tutte le tabelle originali accessibili (tutti gli anni) in Dati NN con indice. Zero distinto da mancante, note testuali senza formula injection. Non contiene credenziali/sessione. Nessuna mutazione applicata dall’export. Ripristino automatico non incluso. Dopo download resta in Fatturato.

11 test JS, build e CI passati. Download browser 2026/2027 e riapertura XLSX riusciti con dati sintetici; valori, record, celle vuote e zero conservati. Anteprima Excel verificata con Artifact Tool. Nessun dato reale modificato.

Prossimo passo: verificare deploy Cloudflare main; non rieseguire migrazione o modificare database. Template originali sono riferimenti di organizzazione: questa esportazione congela i risultati del gestionale e non reintroduce formule obsolete.
