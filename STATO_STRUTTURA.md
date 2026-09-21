# Gestionale Partita IVA — stato della struttura (21 settembre 2026)

## Ambito e riferimento

- App Streamlit con Supabase separato dai gestionali Ordini e Prospect.
- Anno iniziale 2027; foglio originale «calcoli partita iva pietro 2027» usato **solo in lettura** per confronti di formule.
- Fatturato registrato **non** ridotto automaticamente dall'Enasarco.
- Celle vuote e zeri registrati sono concetti diversi; dati dimostrativi sempre distinti dai dati reali.
- Parametri INPS, Enasarco e IRPEF 2027 ancora da verificare su pubblicazioni ufficiali.

## Moduli presenti

1. Fatturato per mandante e mese, proiezione matematica dai mesi compilati.
2. Costi e Auto con registrazioni e stime distinte; alcune percentuali sono soltanto quelle del foglio di prova.
3. Accantonamenti mensili, colonna provvigioni nette manuale persistente e confronto separato delle quote di prova.
4. Caricamento assistito di fatture provvigionali PDF/XML/immagini; conferma esplicita del netto e sostituzione del totale mensile, non somma cieca.
5. Registro IVA acquisti con date operazione/ricezione/registrazione, IVA complessiva, quota detraibile verificata, categoria auto/altro; modifiche ed eliminazioni consentite per anno aperto.
6. Importazione assistita XML FatturaPA acquisti con controllo duplicati; **non** ricava da sola la quota detraibile o la data effettiva di ricezione.
7. Quadro mensile integrato, avvisi di dati mancanti e tre esportazioni CSV locali.
8. Sezione contributi **effettivamente versati**: gli importi non sono inventati o sostituiti con contributi stimati.
9. Controlli automatici di sintassi e test puri nel workflow GitHub, senza credenziali o dati fiscali reali. Verificare l'esito effettivo del workflow prima di dichiarare i test superati.

## Prerequisiti Supabase e accessi

- `SQL_PROVVIGIONI_NETTE.sql` e `SQL_IVA_ACQUISTI.sql` devono essere eseguiti **soltanto** nel progetto Partita IVA.
- Nuovi moduli di questo lotto non richiedono altre tabelle SQL.
- Non accedere tramite service_role: mantenere autenticazione per singolo utente e RLS, come negli script SQL.
- Il collegamento Supabase disponibile in ChatGPT potrebbe NON vedere il progetto Partita IVA. Non modificare progetti Supabase diversi.

## Limiti ancora aperti prima dell'uso fiscale effettivo

- IVA vendite: oggi il 22% del fatturato è **solo scenario del foglio**, non somma delle fatture emesse e di note di credito/aliquote effettive.
- IVA acquisti: una o più fatture registrate non attestano completezza dei documenti; manca riconciliazione univoca con le spese, senza sommare costi due volte.
- Liquidazione IVA: mancano gestione di crediti riportati, rettifiche e modalità effettiva di liquidazione. Non indicare «IVA dovuta» come definitiva.
- Netto mensile: la formula del foglio può essere mostrata soltanto come **ipotesi matematica**; non equivale a denaro disponibile, né netto fiscale.
- IRPEF: applicare la deducibilità dei soli contributi effettivamente versati nell'anno fiscale, inclusi quelli di competenza precedente; le registrazioni sono presenti, il collegamento ai calcoli fiscali effettivi NON è completo.
- Fondo pensione: distinguere versamenti reali, limiti fiscali e impatto sul netto; non promuovere le cifre demo a deduzioni reali.
- Casistiche IVA speciali e fatture di fine anno: richiedono verifica documentale e consulenza prima della liquidazione.
- Test end-to-end nel Supabase corretto, isolamenti RLS delle nuove tabelle, prove con documenti reali e confronto finale con il foglio di origine ancora da eseguire.

**La struttura è in corso di completamento, non è un programma fiscale certificato o pronto per eseguire versamenti.**
