# Passaggio in produzione

Backend vincolato al progetto Personale `mmkjtvebgtwsjatwifjv`, organizzazione `jeekufphnljawewyljsd`. Collaudo distinto `gbtvscldenpmvcvwognw`. Nessun progetto Lavoro o Ordini coinvolto.

1. Completare download CSV e scritture funzionali nel collaudo. Conservare il checkpoint della branch `migration/react-cloudflare` e i risultati della PR bozza 13.
2. Aggiornare la fotografia di schema, policy e conteggi del backend originale. Il controllo attuale in `production-preflight.json` conferma 20 tabelle con RLS e 82 policy; la funzione del completamento struttura non esiste. I 48 moduli fiscali originali sono invariati.
3. Applicare in transazione lo script originale `SQL_COMPLETAMENTO_STRUTTURA.sql`, dopo verifica del ref e dei prerequisiti. Crea soltanto i quattro registri assenti (vendite IVA, periodi IVA, pagamenti pensione, collegamento acquisti/costi), indici, funzione/trigger e relative policy. Nessun dato preesistente viene aggiornato e nessuna policy delle 20 tabelle originali viene modificata. Fotografia dello schema base conservata in `supabase-schema-baseline.json` e `staging-schema.sql`.
4. Rileggere e confrontare integralmente le 82 policy originali. Verificare che i quattro registri nuovi siano vuoti, protetti da RLS e con le stesse definizioni collaudate. Se i prerequisiti differiscono, fermare il passaggio prima di modificare la struttura.
5. Configurare un progetto Pages di produzione separato dal collaudo, con sola chiave publishable e URL del backend Personale. Abilitare la lettura dei quattro registri soltanto dopo il completamento della struttura. Password e chiavi privilegiate non entrano nel frontend.
6. Verificare build, accesso e letture con il backend originale; pubblicare il risultato e il collegamento. Conservare Streamlit e il backup di sicurezza per il ritorno alla versione precedente. Non cancellare dati, tabelle o servizi esistenti.

Il confronto CPython/Pyodide verifica metriche, tabelle e payload CSV delle 16 viste 2026/2027. Le percentuali o gli scenari già descritti come dimostrativi dal codice originale mantengono tale significato; la migrazione non li trasforma in parametri fiscali validati.
