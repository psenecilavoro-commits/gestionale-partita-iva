# Checkpoint produzione — 2026-10-01

Branch migration/react-cloudflare. Ultimo commit applicativo a5daf603b869e8fb902b7d90a9652c1f8d4f7e72. CSV scaricato dall’utente e verificato: 17 colonne, 3 righe sintetiche, totale 300 EUR. File personale non copiato nel repository.

Applicata migrazione react_complete_validated_structure SOLO al backend Personale mmkjtvebgtwsjatwifjv, organizzazione jeekufphnljawewyljsd: script originale SQL_COMPLETAMENTO_STRUTTURA.sql, con sola conferma del progetto sostituita. Adesso 24 tabelle RLS, 99 policy; tutte le 82 policy delle 20 tabelle originali confrontate integralmente e identiche, conteggi pre/post identici; quattro registri nuovi vuoti. Fotografia pre-intervento in production-preflight-2026-10-01.json. Nessun progetto Lavoro/Ordini modificato.

Creato progetto Pages distinto gestionale-partita-iva, URL previsto https://gestionale-partita-iva.pages.dev/, branch provvisoria migration/react-cloudflare, root web, build pnpm build, dist, Node24/pnpm11.19.0. Ambiente production con sola chiave publishable e URL Personale. Il collaudo gestionale-partita-iva-collaudo conserva il suo database separato.

Restano: confrontare nuove definizioni con collaudo, sincronizzare commit, build/test e CI; verificare deploy e schermata di login produzione; controllare accesso anonimo senza dati; rendere PR13 pronta e unire dopo verifiche, passare Pages produzione a main. Aggiornare questa nota con esito. Accesso autenticato ai dati reali richiede login personale dell’utente, mai chiedere password in chat. Streamlit, backup e formule originali conservati.

Nessun lavoro fuori sessione; riprendere da questo checkpoint senza ricreare database o seed.
