# Riporto avanzo — checkpoint 2026-10-03

Implementazione completata. Branch feature/riporto-avanzo, ultimo commit funzionale 3242be3da5a1f3ad065d828bed5b578f3c36ce7d; PR #19 integrata in main con bad06313511005d03ec8c55039822b55cb9d3f89.

Chiusura: aggiornamento atomico status+snapshot nelle notes di fiscal_years, mantenendo le note originali. Snapshot include fabbisogno lordo, riserve, credito entrante, avanzo uscente, token e dipendenza dall’anno precedente. La riapertura rimuove il riepilogo e sospende i riporti dipendenti fino a nuova chiusura coerente. Nessuna formula fiscale, schema o RLS modificati; nessuna chiusura reale eseguita.

Verifiche: 52 test Python, 6 bridge React, 10 JavaScript con equivalenza CPython/Pyodide per 16 viste, build e CI passati. Browser collaudo demo: chiusura 2026 produce 5.128,84 euro per 2027; riapertura sospende; nuova chiusura dopo modifica sintetica produce 6.128,84 euro. Dati reali non utilizzati nei test.

Prossimo passo: verificare il deploy Cloudflare produzione di main. Non rieseguire la migrazione, non chiudere anni reali come test, non ricreare Supabase di collaudo.
