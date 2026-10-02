# Correzione indicazione IVA inclusa — 2026-10-02

L’utente ha confermato che tutti gli importi della schermata Costi2026 sono IVA compresa. Lo script SQL_IMPORTA_2026_FORFETTARIO.sql aveva impostato false sulle spese e stime importate: corretti i due valori di importazione a true, senza rieseguire l’importazione.

Sul solo Supabase Personale mmkjtvebgtwsjatwifjv, per il proprietario della schermata e anno2026 aperto, aggiornati27 costi con nota esatta IMPORTATO DA FILE2026 (giorno01 tecnico) e11 stime importate. Transazione con conteggi attesi e confronto JSON di ogni campo escluso amount_includes_vat prima/dopo: nessun altro campo modificato. Verifica finale27/27 costi IVA inclusa. RLS e formule Python invariate. Rollback: ripristinare false soltanto per questi stessi record importati e anno/proprietario, dopo controllo di eventuali modifiche successive.

Frontend mostra IVA compresa Sì/No invece di true/false. Build riuscita. Commit applicativi6a00a271 (visualizzazione) e93c892f (script). Riprendere da main; non reimportare né ricreare dati.
