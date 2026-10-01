# Checkpoint produzione pronta — 2026-10-01

La migrazione è stata unita in main con PR13, commit 706ac7866408c35084d91cb93ddf978b951aea2f. Ultimo commit applicativo ed71c7e9d14d9d169a7d8a9c7049506aa498d268. Entrambe CI passate, build e cinque test Node passati. I 48 moduli fiscali Python originali sono identici alla baseline a6152b1366fe80cce950bc927a9099e728005cba; confronti CPython/Pyodide di 16 viste e CSV riusciti.

Produzione https://gestionale-partita-iva.pages.dev/ pubblicata: deploy f18a57a5-8340-42e5-a4c3-def9b2292036 riuscito, schermata login verificata. Pages ora segue main, ambiente production, backend Supabase Personale mmkjtvebgtwsjatwifjv. Pubblica soltanto la chiave publishable. Nessuna lettura anonima restituisce dati sulle24 tabelle.

Applicata SOLO a Personale migrazione react_complete_validated_structure con lo script SQL_COMPLETAMENTO_STRUTTURA.sql originale: aggiunti quattro registri già collaudati, 24 tabelle RLS/99 policy. Tutte le82 policy originali identiche, tutti i conteggi pre/post invariati, quattro nuove tabelle vuote; nuova funzione/policy identiche al collaudo. Fotografia pre-DDL in production-preflight-2026-10-01.json. Nessun progetto Lavoro/Ordini toccato.

Il CSV allegato dall’utente conferma il download: 17 colonne, tre spese sintetiche, totale300 EUR. Il file non è stato copiato nel repository. Collaudo https://gestionale-partita-iva-collaudo.pages.dev/ conserva Supabase separato gbtvscldenpmvcvwognw; non rieseguire seed. Backup pre-react e Streamlit conservati.

Prossimo passo esatto: l’utente accede alla produzione con il proprio account Supabase esistente e verifica i dati reali. Non chiedere password in chat e non creare utenti sintetici in produzione. La verifica autenticata su dati reali non è stata effettuata dall’agente. Se serve proseguire, partire da main e da questo checkpoint, non dalla baseline. Nessun processo o lavoro fuori sessione.
