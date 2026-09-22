-- SOLO LETTURA. Eseguire esclusivamente nel SQL Editor del SECONDO Supabase,
-- progetto Gestionale Partita IVA, dopo aver verificato URL/ref e backup.
-- Non usare nei progetti Ordini e Prospect. Non elimina o modifica alcuna riga.
-- Gli importi immessi a mano senza un marcatore demo NON sono identificabili
-- automaticamente: controllarli anche dall'interfaccia del gestionale.

DO $$
BEGIN
  IF to_regclass('public.fiscal_years') IS NULL
     OR to_regclass('public.monthly_revenues') IS NULL
     OR to_regclass('public.annual_cost_estimates') IS NULL
     OR to_regclass('public.cost_categories') IS NULL
     OR to_regclass('public.costs') IS NULL
     OR to_regclass('public.vehicle_monthly') IS NULL
     OR to_regclass('public.vehicle_year_settings') IS NULL
     OR to_regclass('public.vehicles') IS NULL
     OR to_regclass('public.fiscal_parameters') IS NULL THEN
    RAISE EXCEPTION 'Schema del Gestionale Partita IVA non riconosciuto: nessuna operazione';
  END IF;
END $$;

-- Totale per tipologia, limitato al solo anno 2027 (il veicolo è globale).
SELECT 'Fatturato dimostrativo' AS tipo, count(*) AS righe
FROM public.monthly_revenues r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'Spese dimostrative', count(*)
FROM public.costs r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'Stime annuali dimostrative', count(*)
FROM public.annual_cost_estimates r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'Percorrenza dimostrativa', count(*)
FROM public.vehicle_monthly r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'Limite e penale dimostrativi', count(*)
FROM public.vehicle_year_settings r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'Parametri fiscali caricati come esempio', count(*)
FROM public.fiscal_parameters r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.source LIKE 'CONFRONTO NON VERIFICATO: foglio originale %'
UNION ALL SELECT 'Categorie demo orfane del 2027', count(*)
FROM public.cost_categories c JOIN public.fiscal_years f ON f.id=c.fiscal_year_id
WHERE f.fiscal_year=2027
  AND c.notes='Parametri di confronto dal foglio; verificare prima dell''uso reale.'
  AND NOT EXISTS (SELECT 1 FROM public.costs x WHERE x.category_id=c.id AND x.notes NOT LIKE 'DATI DI PROVA%')
  AND NOT EXISTS (SELECT 1 FROM public.annual_cost_estimates x WHERE x.category_id=c.id AND x.notes NOT LIKE 'DATI DI PROVA%')
UNION ALL SELECT 'Veicoli demo candidati (solo se poi senza legami)', count(*)
FROM public.vehicles v
WHERE v.notes='VEICOLO DI PROVA - foglio originale';

-- Identificativi e importi candidati: verificare che NON siano stati riutilizzati
-- o modificati manualmente prima di procedere alla cancellazione.
SELECT 'fatturato' AS tabella, r.id::text AS id, f.fiscal_year AS anno,
       concat('Mese ',r.month, ' · ',r.amount,' € · ',r.notes) AS dettaglio
FROM public.monthly_revenues r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'costi',r.id::text,f.fiscal_year,
       concat(r.expense_date,' · ',r.description,' · ',r.gross_amount,' € · ',r.notes)
FROM public.costs r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'stime',r.id::text,f.fiscal_year,
       concat(r.estimated_gross_amount,' € · ',r.notes)
FROM public.annual_cost_estimates r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'percorrenza',r.id::text,f.fiscal_year,
       concat('Mese ',r.month,' · ',r.distance_km,' km · ',r.notes)
FROM public.vehicle_monthly r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'limite e penale',r.id::text,f.fiscal_year,
       concat(r.annual_km_limit,' km · ',r.excess_km_penalty,' €/km · ',r.notes)
FROM public.vehicle_year_settings r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.notes LIKE 'DATI DI PROVA%'
UNION ALL SELECT 'parametro fiscale',r.id::text,f.fiscal_year,
       concat(r.code,' = ',r.value,' · ',r.source)
FROM public.fiscal_parameters r JOIN public.fiscal_years f ON f.id=r.fiscal_year_id
WHERE f.fiscal_year=2027 AND r.source LIKE 'CONFRONTO NON VERIFICATO: foglio originale %'
ORDER BY tabella,anno,dettaglio;
