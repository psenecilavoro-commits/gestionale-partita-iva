-- RESET OPERATIVO 2027
-- Eseguire SOLO nel Supabase del Gestionale Partita IVA (secondo account).
-- Cancella i dati operativi del 2027 ma conserva:
--   * la riga dell'anno fiscale 2027;
--   * le mandanti (principals);
--   * i parametri fiscali (fiscal_parameters);
--   * le detrazioni pluriennali/globali (tax_credits);
--   * la struttura, RLS e le tabelle.
--
-- Lo script è transazionale: se un controllo fallisce, non viene cancellato nulla.
-- Prima di eseguirlo sostituire DA_CONFERMARE con CONFERMO_RESET_2027.

begin;
set local app.confirm_reset_piva_2027 = 'DA_CONFERMARE';

create temporary table reset_2027_report (
  voce text not null,
  righe_cancellate integer not null
) on commit drop;

do $$
declare
  y uuid;
  stato text;
  n integer;
  t text;
  esistenti integer;
  remaining integer;
  tabelle text[] := array[
    'purchase_cost_links',
    'sales_vat_invoices',
    'vat_periods',
    'pension_payments',
    'monthly_net_commissions',
    'monthly_reserves',
    'purchase_vat_invoices',
    'tax_deductions',
    'depreciable_assets',
    'monthly_revenues',
    'costs',
    'annual_cost_estimates',
    'vehicle_monthly',
    'vehicle_year_settings',
    'cost_categories'
  ];
begin
  if current_setting('app.confirm_reset_piva_2027', true)
       is distinct from 'CONFERMO_RESET_2027' then
    raise exception
      'Reset bloccato: verificare il progetto Partita IVA e sostituire DA_CONFERMARE con CONFERMO_RESET_2027';
  end if;

  if to_regclass('public.fiscal_years') is null then
    raise exception 'Schema non riconosciuto: fiscal_years assente';
  end if;

  select count(*) into esistenti
  from public.fiscal_years
  where fiscal_year = 2027;

  if esistenti = 0 then
    raise exception 'Anno fiscale 2027 non trovato: nessuna cancellazione';
  elsif esistenti > 1 then
    raise exception
      'Trovate % righe per il 2027: reset annullato per evitare di cancellare dati di più utenti',
      esistenti;
  end if;

  select id, status into y, stato
  from public.fiscal_years
  where fiscal_year = 2027;

  if stato is distinct from 'open' then
    raise exception 'Anno 2027 non aperto (stato=%): reset annullato', stato;
  end if;

  -- Cancellazione ordinata dei dati annuali. Le tabelle opzionali non presenti
  -- vengono semplicemente ignorate.
  foreach t in array tabelle loop
    if to_regclass(format('public.%I', t)) is not null
       and exists (
         select 1
         from information_schema.columns
         where table_schema='public'
           and table_name=t
           and column_name='fiscal_year_id'
       ) then
      execute format('delete from public.%I where fiscal_year_id = $1', t) using y;
      get diagnostics n = row_count;
      insert into pg_temp.reset_2027_report(voce, righe_cancellate)
      values (t, n);
    end if;
  end loop;

  -- Elimina il solo veicolo dimostrativo storico se, dopo il reset, è rimasto
  -- completamente scollegato da qualsiasi anno. I veicoli reali restano.
  if to_regclass('public.vehicles') is not null then
    delete from public.vehicles v
    where v.notes = 'VEICOLO DI PROVA - foglio originale'
      and (
        to_regclass('public.costs') is null
        or not exists (select 1 from public.costs c where c.vehicle_id = v.id)
      )
      and (
        to_regclass('public.vehicle_monthly') is null
        or not exists (select 1 from public.vehicle_monthly m where m.vehicle_id = v.id)
      )
      and (
        to_regclass('public.vehicle_year_settings') is null
        or not exists (select 1 from public.vehicle_year_settings s where s.vehicle_id = v.id)
      );
    get diagnostics n = row_count;
    insert into pg_temp.reset_2027_report(voce, righe_cancellate)
    values ('vehicles_demo_orfani', n);
  end if;

  -- Controllo finale: nessuna tabella annuale gestita deve conservare righe 2027.
  foreach t in array tabelle loop
    if to_regclass(format('public.%I', t)) is not null
       and exists (
         select 1
         from information_schema.columns
         where table_schema='public'
           and table_name=t
           and column_name='fiscal_year_id'
       ) then
      execute format('select count(*) from public.%I where fiscal_year_id = $1', t)
        into remaining using y;
      if remaining <> 0 then
        raise exception
          'Reset incompleto: la tabella % conserva ancora % righe del 2027',
          t, remaining;
      end if;
    end if;
  end loop;

  -- Le configurazioni che devono restare vengono verificate, non cancellate.
  if not exists (select 1 from public.fiscal_years where id=y and fiscal_year=2027) then
    raise exception 'Errore: la riga fiscal_years 2027 non è più presente';
  end if;

  if to_regclass('public.fiscal_parameters') is not null then
    select count(*) into n
    from public.fiscal_parameters
    where fiscal_year_id=y;
    insert into pg_temp.reset_2027_report(voce, righe_cancellate)
    values ('fiscal_parameters_conservati', -n);
  end if;
end $$;

-- Valori >= 0 = righe cancellate.
-- Per fiscal_parameters_conservati il numero negativo indica quante righe
-- sono state volutamente conservate.
select voce, righe_cancellate
from pg_temp.reset_2027_report
order by voce;

commit;
