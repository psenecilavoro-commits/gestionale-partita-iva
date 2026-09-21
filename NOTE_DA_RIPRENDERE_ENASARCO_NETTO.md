# Vincoli di progetto: fatturato, Enasarco, netto e formule

## Chiarimento esplicito dell'utente (20 settembre 2026) — PREVALE sulle note precedenti

**L'Enasarco NON deve essere sottratto dal fatturato.** La precedente nota secondo cui in Fatturato si dovrebbe registrare «fatturato meno Enasarco» era un'interpretazione errata e NON va implementata. L'utente ha chiarito che l'Enasarco viene trattenuto a monte nel flusso di pagamento/fatturazione, ma non deve ridurre il valore denominato FATTURATO nel gestionale. Mantenere distinti fatturato, trattenuta Enasarco e incasso/disponibilità effettivi; non inventare una formula che li confonda.

**Per tutte le formule dell'app il riferimento funzionale è SEMPRE il foglio originale** «calcoli partita iva pietro 2027» (Google Sheet ID `1-FsiHFWzuEWmRbASdeSrowjIE73U5-GanDJkn5tEzAE`), da consultare in sola lettura prima di sviluppare ciascun calcolo. Riprodurre fedelmente le formule, i riferimenti fra schede, le celle manuali e gli arrotondamenti per i test; se un'ipotesi del foglio è incerta o un parametro fiscale 2027 non è verificato, segnalare esplicitamente e non sostituire tacitamente la formula con un'altra. Non scrivere nel foglio.

## Riferimenti effettivamente riscontrati nel foglio

- `Fatturato!B41` = `SUM(17:17)` e vale 115.200 € nel test. `Conto economico!B1` = `Fatturato!B41`: il fatturato viene riportato per intero, senza sottrarre Enasarco.
- `Fatturato!B19/E19/H19/K19`: le quote Enasarco sono calcolate *separatamente* sulle stime delle rispettive mandanti usando l'aliquota 0,085 e il massimale di riferimento nel foglio. `Imposte!E4` somma quelle quote (5.206,845 € nel test).
- Il foglio usa `Imposte!E4` in `Conto economico!B8` (`=B1-Costi!F14-Imposte!E4`) e `Conto economico!B9` (`=B1-Costi!F14-Imposte!E4-Imposte!B3-Imposte!B5-'Detrazioni e deduzioni'!I3`). Ciò riguarda le *basi di calcolo* del foglio, non è un'istruzione per diminuire il campo FATTURATO. L'effettiva correttezza fiscale e i parametri 2027 dovranno essere verificati prima di usare le formule come risultati definitivi.
- `Tabella accantonamenti!C2` usa `=B2-D2-J2`, ma la colonna B «PROVV. NETTE» è inserita manualmente nel foglio e non coincide automaticamente con il fatturato. Non chiamare netto la differenza attuale `fatturato - accantonato` dell'app.

## Da riprendere quando completiamo Imposte e Tabella accantonamenti

1. Distinguere provvigioni/fatturato, Enasarco personale, fattura, IVA, incasso e disponibilità senza deduzioni doppie. Per l'esempio esplicativo dell'utente, 10.000 € e trattenuta 850 € sono importi illustrativi e NON una regola generale o una formula del fatturato.
2. Concordare come alimentare il valore mensile «PROVV. NETTE» (nel foglio compilato a mano), il netto mensile e l'accantonato; non inventare un automatismo prima di conoscere la provenienza dei dati.
3. Confrontare ogni calcolo dell'app con le formule e i risultati del foglio originale, conservando la distinzione fra test e dati reali. Verificare separatamente aliquote, massimali e trattamento contributivo/fiscale 2027.

Questa nota non modifica né i dati presenti né i calcoli attualmente attivi nell'app.

## Aggiornamento strutturazione Codex — 21 settembre 2026

Foglio riletto in sola lettura. Confermata anche `Tabella accantonamenti!E16 = E17-H18`: H18 (avanzo A.P.) ora è un input esplicito dello scenario. Il confronto letterale del Conto economico resta invariato; la variante sulle registrazioni applica separatamente il totale INPS pagato nell'anno (incluso A.P. una sola volta), Enasarco documentato e pensione entro un limite manuale di scenario. Il fatturato resta integrale. Nessuna aliquota o deduzione 2027 è stata promossa a regola fiscale verificata. Vedere stato e handover per prerequisiti SQL non applicati e limiti del collaudo.
