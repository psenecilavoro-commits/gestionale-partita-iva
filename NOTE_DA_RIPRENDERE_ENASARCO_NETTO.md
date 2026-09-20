# Da riprendere prima di completare Imposte e Tabella accantonamenti

Stato: **decisione funzionale sospesa — non implementare automaticamente una formula del netto**.

## Precisazione dell'utente (20 settembre 2026)

- Per il suo rapporto commerciale, la quota Enasarco a suo carico viene trattenuta a monte al momento della fatturazione. Esempio fornito dall'utente: provvigioni di riferimento 10.000 € e trattenuta Enasarco 850 €; l'importo da registrare nella sua operatività è 9.150 € (10.000 − 850). **850 € è un esempio dell'utente, non una percentuale da applicare indistintamente.**
- Nella scheda **Fatturato**, l'utente desidera registrare l'importo al netto della trattenuta Enasarco, secondo la modalità descritta. Evitare di detrarre una seconda volta l'Enasarco da quello stesso importo nei riepiloghi di disponibilità.
- La **Tabella accantonamenti** serve principalmente per annotare il **netto mensile disponibile**, non solo la differenza tra un importo di fatturato e gli accantonamenti. Nel foglio originale l'utente inseriva manualmente il NETTO proprio perché il dato non si ricavava direttamente dalle colonne già compilate.
- La precedente implementazione della Tabella accantonamenti mostra una differenza `provvigioni - accantonato` con avviso che non è netto fiscale: **non chiamarla netto disponibile o netto fiscale** e non trattarla come risultato definitivo.

## Verifiche progettuali prima dell'implementazione

1. Concordare con l'utente il significato preciso e le fonti di ciascun importo: provvigioni contrattuali, trattenuta Enasarco a suo carico, importo indicato in fattura, imponibile IVA, IVA esposta e pagamento incassato. Non presumere che tutti coincidano o che la trattenuta modifichi automaticamente l'imponibile IVA/fiscale.
2. Esaminare insieme la scheda **Imposte** e verificare come viene già calcolato Enasarco, per evitare conteggi doppi o mancanti in Fatturato, Conto economico e accantonamenti.
3. Definire se il NETTO mensile sia un campo manuale modificabile come nel foglio, un calcolo con rettifica manuale, o entrambi; distinguerlo dalla disponibilità bancaria e dal netto annuo fiscale.
4. Tenere separate le registrazioni di prova dalle registrazioni reali; confermare il trattamento fiscale e contributivo aggiornato prima di attivare calcoli automatici definitivi.

**Nessuna modifica ai dati o alle formule applicative viene richiesta da questa nota.**
