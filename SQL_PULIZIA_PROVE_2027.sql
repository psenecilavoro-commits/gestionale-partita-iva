-- PULIZIA MIRATA E IRREVERSIBILE: eseguire SOLO dopo backup e anteprima.
-- 1. Verificare personalmente nome e URL/ref del SECONDO progetto Supabase,
--    dedicato al Gestionale Partita IVA. NON usare Ordini o Prospect.
-- 2. Eseguire SQL_ANTEPRIMA_PULIZIA_PROVE_2027.sql e controllare OGNI riga.
-- 3. Solo dopo, sostituire DA_CONFERMARE con CONFERMO_SOLO_PARTITA_IVA.
-- Non eliminare l'anno 2027, le mandanti, dati reali, documenti, crediti,
-- deduzioni né parametri inseriti o modificati manualmente.
-- I record inseriti a mano senza marcatori di prova richiedono revisione
-- manuale: non è possibile distinguerli con certezza da quelli reali.

BEGIN;
SET LOCAL app.confirm_partita_iva = 'DA_CONFERMARE';

DO $$
BEGIN
  IF current_setting('app.confirm_partita_iva', true) IS DISTINCT FROM 'CONFERMO_SOLO_PARTITA_IVA' THEN
    RAISE EXCEPTION 'Script bloccato: controllare progetto, backup e anteprima prima di confermare';
  END IF;
  IF to_regclass('public.fiscal_years') IS NULL
     OR to_regclass('public.monthly_revenues') IS NULL
     OR to_regclass('public.costs') IS NULL
     OR to_regclass('public.annual_cost_estimates') IS NULL
     OR to_regclass('public.cost_categories') IS NULL
     OR to_regclass('public.vehicle_monthly') IS NULL
     OR to_regclass('public.vehicle_year_settings') IS NULL
     OR to_regclass('public.vehicles') IS NULL
     OR to_regclass('public.fiscal_parameters') IS NULL THEN
    RAISE EXCEPTION 'Schema Partita IVA incompleto: cancellazione annullata';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.fiscal_years WHERE fiscal_year = 2027) THEN
    RAISE EXCEPTION 'Anno fiscale 2027 non presente: cancellazione annullata';
  END IF;
END $$;

-- Identificatori contrassegnati esplicitamente come DATI DI PROVA,
-- nell'anno 2027 soltanto. Le righe ordinarie rimangono intatte.
DELETE FROM public.monthly_revenues r USING public.fiscal_years f
WHERE r.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND r.notes LIKE 'DATI DI PROVA%';

DELETE FROM public.costs r USING public.fiscal_years f
WHERE r.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND r.notes LIKE 'DATI DI PROVA%';

DELETE FROM public.annual_cost_estimates r USING public.fiscal_years f
WHERE r.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND r.notes LIKE 'DATI DI PROVA%';

DELETE FROM public.vehicle_monthly r USING public.fiscal_years f
WHERE r.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND r.notes LIKE 'DATI DI PROVA%';

DELETE FROM public.vehicle_year_settings r USING public.fiscal_years f
WHERE r.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND r.notes LIKE 'DATI DI PROVA%';

-- Solo parametri caricati automaticamente dallo scenario originario.
-- Quelli modificati dall'utente hanno una fonte differente e si conservano.
DELETE FROM public.fiscal_parameters r USING public.fiscal_years f
WHERE r.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND r.source LIKE 'CONFRONTO NON VERIFICATO: foglio originale %';

-- Categorie storiche di test: eliminare SOLO se rimaste realmente vuote.
DELETE FROM public.cost_categories c USING public.fiscal_years f
WHERE c.fiscal_year_id = f.id AND f.fiscal_year = 2027
  AND c.notes = 'Parametri di confronto dal foglio; verificare prima dell''uso reale.'
  AND NOT EXISTS (SELECT 1 FROM public.costs x WHERE x.category_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM public.annual_cost_estimates x WHERE x.category_id = c.id);

-- Il veicolo demo è globale: conservarlo se ci sono ancora riferimenti,
-- anche in altri anni o da documenti non trattati da questa pulizia.
DELETE FROM public.vehicles v
WHERE v.notes = 'VEICOLO DI PROVA - foglio originale'
  AND NOT EXISTS (SELECT 1 FROM public.costs x WHERE x.vehicle_id = v.id)
  AND NOT EXISTS (SELECT 1 FROM public.vehicle_monthly x WHERE x.vehicle_id = v.id)
  AND NOT EXISTS (SELECT 1 FROM public.vehicle_year_settings x WHERE x.vehicle_id = v.id);

COMMIT;

-- Controllo finale: eseguire nuovamente lo script di ANTEPRIMA e verificare
-- che non restino righe contrassegnate; controllare anche l'app con F5.
