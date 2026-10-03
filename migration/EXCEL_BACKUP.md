# Backup Excel — checkpoint 2026-10-03

Branch feature/backup-excel, base 4c659ef48b1223c97fc4aa54728dd560d279da57. Pulsante nella riga Esci solo in Fatturato. ExcelJS lazy load, elaborazione locale; export prospetti otto schede dell’anno selezionato col motore Python esistente, risultati fissati e tutte le tabelle originali accessibili (tutti gli anni) in Dati NN con indice. Zero distinto da mancante, note testuali senza formula injection. Non contiene credenziali/sessione. Nessuna mutazione applicata dall’export. Ripristino automatico non incluso.

11 test JS passati, build completata. Prossimo passo: deploy collaudo demo, prova download 2026/2027, verifica file e poi PR/CI/produzione. Non rieseguire migrazione, non modificare database.
