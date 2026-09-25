-- IMPORTA ANNO 2026 · REGIME FORFETTARIO
-- Fonte: "calcoli partita iva pietro 2026.xlsx" caricato il 25/09/2026.
-- Eseguire SOLO nel Supabase del Gestionale Partita IVA (organizzazione Personale).
-- Non usare nei progetti Gestionale Ordini o Gestionale Prospect.
--
-- Lo script:
--   * crea l'anno fiscale 2026 se assente;
--   * riusa le quattro mandanti già esistenti (o le crea se mancanti);
--   * importa fatturato, provvigioni nette, accantonamenti, auto e costi del file;
--   * carica i parametri necessari al modello forfettario 2026;
--   * NON crea registrazioni IVA vendite/acquisti;
--   * NON modifica il 2027.
--
-- Sicurezza: se trova dati operativi già presenti nel 2026, interrompe tutto.
-- Prima di Run sostituire DA_CONFERMARE con CONFERMO_IMPORT_2026.

begin;
set local app.confirm_import_piva_2026 = 'DA_CONFERMARE';

create temporary table piva_import_2026_context (
  fiscal_year_id uuid not null,
  owner_id uuid not null
) on commit drop;

do $$
declare
  owner_id uuid;
  y2026 uuid;
  y2027_count integer;
  n integer;
  t text;
  v_id uuid;
  p_caino uuid;
  p_borgo uuid;
  p_erbe uuid;
  p_fontanella uuid;
  has_vehicle_owner boolean;
  tabelle_annuali text[] := array[
    'monthly_revenues',
    'monthly_reserves',
    'monthly_net_commissions',
    'vehicle_monthly',
    'vehicle_year_settings',
    'cost_categories',
    'annual_cost_estimates',
    'costs',
    'fiscal_parameters',
    'sales_vat_invoices',
    'purchase_vat_invoices',
    'vat_periods',
    'pension_payments',
    'tax_deductions',
    'depreciable_assets',
    'purchase_cost_links'
  ];
begin
  if current_setting('app.confirm_import_piva_2026', true)
       is distinct from 'CONFERMO_IMPORT_2026' then
    raise exception
      'Import bloccato: verifica il progetto Partita IVA e sostituisci DA_CONFERMARE con CONFERMO_IMPORT_2026';
  end if;

  if to_regclass('public.fiscal_years') is null
     or to_regclass('public.principals') is null
     or to_regclass('public.monthly_revenues') is null
     or to_regclass('public.monthly_reserves') is null
     or to_regclass('public.monthly_net_commissions') is null
     or to_regclass('public.vehicles') is null
     or to_regclass('public.vehicle_monthly') is null
     or to_regclass('public.vehicle_year_settings') is null
     or to_regclass('public.cost_categories') is null
     or to_regclass('public.annual_cost_estimates') is null
     or to_regclass('public.costs') is null
     or to_regclass('public.fiscal_parameters') is null then
    raise exception 'Schema del Gestionale Partita IVA incompleto: import annullato';
  end if;

  -- Il 2027 è già stato creato e pulito: viene usato solo per identificare
  -- il proprietario corretto. Nessuna riga 2027 viene modificata.
  select count(*) into y2027_count
  from public.fiscal_years
  where fiscal_year = 2027;

  if y2027_count <> 1 then
    raise exception
      'Attese esattamente 1 riga fiscal_years per il 2027, trovate %: import annullato',
      y2027_count;
  end if;

  select user_id into owner_id
  from public.fiscal_years
  where fiscal_year = 2027;

  select id into y2026
  from public.fiscal_years
  where fiscal_year = 2026 and user_id = owner_id
  limit 1;

  if y2026 is null then
    insert into public.fiscal_years(user_id, fiscal_year, status)
    values (owner_id, 2026, 'open')
    returning id into y2026;
  elsif (select status from public.fiscal_years where id = y2026) <> 'open' then
    raise exception 'L''anno 2026 esiste ma non è aperto: import annullato';
  end if;

  -- Mai sovrascrivere un 2026 già utilizzato.
  foreach t in array tabelle_annuali loop
    if to_regclass(format('public.%I', t)) is not null
       and exists (
         select 1 from information_schema.columns
         where table_schema = 'public'
           and table_name = t
           and column_name = 'fiscal_year_id'
       ) then
      execute format('select count(*) from public.%I where fiscal_year_id = $1', t)
        into n using y2026;
      if n <> 0 then
        raise exception
          'Il 2026 contiene già % righe nella tabella %: import annullato senza modifiche',
          n, t;
      end if;
    end if;
  end loop;

  insert into pg_temp.piva_import_2026_context(fiscal_year_id, owner_id)
  values (y2026, owner_id);

  -- Mandanti: riusa quelle globali del gestionale, senza duplicarle.
  if (select count(*) from public.principals
      where user_id = owner_id and lower(btrim(name)) = lower('Innovagroup Caino')) > 1 then
    raise exception 'Mandante Innovagroup Caino duplicata: import annullato';
  end if;
  if (select count(*) from public.principals
      where user_id = owner_id and lower(btrim(name)) = lower('Innovagroup Borgo')) > 1 then
    raise exception 'Mandante Innovagroup Borgo duplicata: import annullato';
  end if;
  if (select count(*) from public.principals
      where user_id = owner_id and lower(btrim(name)) = lower('Innovagroup Erbe')) > 1 then
    raise exception 'Mandante Innovagroup Erbe duplicata: import annullato';
  end if;
  if (select count(*) from public.principals
      where user_id = owner_id and lower(btrim(name)) = lower('Innovagroup Fontanella')) > 1 then
    raise exception 'Mandante Innovagroup Fontanella duplicata: import annullato';
  end if;

  insert into public.principals(user_id, name, enasarco_relationship)
  select owner_id, x.name, 'plurimandatario'
  from (values
    ('Innovagroup Caino'),
    ('Innovagroup Borgo'),
    ('Innovagroup Erbe'),
    ('Innovagroup Fontanella')
  ) as x(name)
  where not exists (
    select 1 from public.principals p
    where p.user_id = owner_id
      and lower(btrim(p.name)) = lower(x.name)
  );

  select id into p_caino from public.principals
  where user_id=owner_id and lower(btrim(name))=lower('Innovagroup Caino');
  select id into p_borgo from public.principals
  where user_id=owner_id and lower(btrim(name))=lower('Innovagroup Borgo');
  select id into p_erbe from public.principals
  where user_id=owner_id and lower(btrim(name))=lower('Innovagroup Erbe');
  select id into p_fontanella from public.principals
  where user_id=owner_id and lower(btrim(name))=lower('Innovagroup Fontanella');

  -- Fatturato: soltanto i mesi compilati nel file (febbraio-settembre).
  -- Gennaio e ottobre-dicembre restano VUOTI, come nel foglio, per non alterare
  -- le proiezioni basate sul numero dei mesi compilati.
  insert into public.monthly_revenues
    (fiscal_year_id, principal_id, month, amount, notes)
  values
    (y2026,p_caino,2,3867.66,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,3,4938.62,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,4,6733.52,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,5,9708.97,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,6,7247.88,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,7,9188.22,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,8,9271.93,'IMPORTATO DA FILE 2026'),
    (y2026,p_caino,9,6564.78,'IMPORTATO DA FILE 2026'),

    (y2026,p_borgo,2,707.46,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,3,798.19,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,4,1021.84,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,5,1309.53,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,6,1186.80,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,7,1139.54,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,8,1492.83,'IMPORTATO DA FILE 2026'),
    (y2026,p_borgo,9,439.14,'IMPORTATO DA FILE 2026'),

    (y2026,p_erbe,2,855.93,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,3,497.70,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,4,1293.11,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,5,1394.51,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,6,1561.74,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,7,860.63,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,8,1912.14,'IMPORTATO DA FILE 2026'),
    (y2026,p_erbe,9,981.55,'IMPORTATO DA FILE 2026'),

    (y2026,p_fontanella,2,533.45,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,3,682.26,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,4,703.53,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,5,310.81,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,6,625.45,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,7,203.74,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,8,587.95,'IMPORTATO DA FILE 2026'),
    (y2026,p_fontanella,9,195.57,'IMPORTATO DA FILE 2026');

  -- Provvigioni nette e somme accantonate presenti nel foglio.
  insert into public.monthly_net_commissions(fiscal_year_id, month, amount)
  values
    (y2026,1,0.00),
    (y2026,2,5457.53),
    (y2026,3,6329.19),
    (y2026,4,8923.25),
    (y2026,5,11646.21),
    (y2026,6,9894.53),
    (y2026,7,11208.88),
    (y2026,8,12927.62),
    (y2026,9,8047.66);

  insert into public.monthly_reserves(fiscal_year_id, month, reserved_amount, notes)
  values
    (y2026,1,0.00,'IMPORTATO DA FILE 2026'),
    (y2026,2,2329.00,'IMPORTATO DA FILE 2026'),
    (y2026,3,1492.00,'IMPORTATO DA FILE 2026'),
    (y2026,4,3550.00,'IMPORTATO DA FILE 2026'),
    (y2026,5,5031.76,'IMPORTATO DA FILE 2026'),
    (y2026,6,3010.50,'IMPORTATO DA FILE 2026'),
    (y2026,7,5000.00,'IMPORTATO DA FILE 2026'),
    (y2026,8,7000.00,'IMPORTATO DA FILE 2026'),
    (y2026,9,3000.00,'IMPORTATO DA FILE 2026');

  -- Auto: usa l'unico veicolo reale già presente; se non c'è, lo crea.
  select exists (
    select 1 from information_schema.columns
    where table_schema='public' and table_name='vehicles' and column_name='user_id'
  ) into has_vehicle_owner;

  if has_vehicle_owner then
    execute
      'select count(*) from public.vehicles where user_id=$1 and coalesce(notes,'''') <> $2'
      into n using owner_id, 'VEICOLO DI PROVA - foglio originale';
  else
    select count(*) into n from public.vehicles
    where coalesce(notes,'') <> 'VEICOLO DI PROVA - foglio originale';
  end if;

  if n > 1 then
    raise exception 'Sono presenti più veicoli reali: import 2026 annullato';
  elsif n = 0 then
    if has_vehicle_owner then
      execute
        'insert into public.vehicles(user_id,label,notes) values($1,$2,$3) returning id'
        into v_id using owner_id, 'Auto', 'IMPORTATO DA FILE 2026';
    else
      insert into public.vehicles(label,notes)
      values ('Auto','IMPORTATO DA FILE 2026')
      returning id into v_id;
    end if;
  else
    if has_vehicle_owner then
      execute
        'select id from public.vehicles where user_id=$1 and coalesce(notes,'''') <> $2 limit 1'
        into v_id using owner_id, 'VEICOLO DI PROVA - foglio originale';
    else
      select id into v_id from public.vehicles
      where coalesce(notes,'') <> 'VEICOLO DI PROVA - foglio originale'
      limit 1;
    end if;
  end if;

  insert into public.vehicle_monthly
    (fiscal_year_id,vehicle_id,month,distance_km,notes)
  values
    (y2026,v_id,1,0,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,2,2093,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,3,1616,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,4,1839,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,5,1888,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,6,1118,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,7,1551,'IMPORTATO DA FILE 2026'),
    (y2026,v_id,8,1334,'IMPORTATO DA FILE 2026');

  insert into public.vehicle_year_settings
    (fiscal_year_id,vehicle_id,annual_km_limit,excess_km_penalty,notes)
  values
    (y2026,v_id,50000,0.16,'IMPORTATO DA FILE 2026');

  -- Categorie economiche del 2026 forfettario.
  -- Le percentuali analitiche IVA/deducibilità sono volutamente 0: nel modello
  -- 2026 queste spese servono al netto economico, non a determinare il reddito
  -- tramite deduzione analitica.
  insert into public.cost_categories
    (fiscal_year_id,code,name,vat_rate,vat_deductible_rate,cost_deductible_rate,notes)
  values
    (y2026,'rate_auto','Auto · rate',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'penale_km','Penale km',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'carburante','Carburante',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'autostrada','Autostrada',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'bollo','Bollo',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'assicurazione','Assicurazione',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'manutenzione_auto','Manutenzione auto',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'commercialista','Commercialista',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'gestionale','Gestionale',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'pc','PC',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario'),
    (y2026,'telefono_tablet','Telefono o tablet',0,0,0,'IMPORTATO DA FILE 2026 · regime forfettario');

  -- Stime annuali del foglio. Gli importi sono memorizzati ai centesimi:
  -- eventuali frazioni di centesimo delle formule Excel vengono arrotondate.
  insert into public.annual_cost_estimates
    (fiscal_year_id,category_id,estimated_gross_amount,amount_includes_vat,notes)
  select y2026,c.id,x.amount,false,'IMPORTATO DA FILE 2026 · STIMA ANNUA'
  from (values
    ('rate_auto',6388.42::numeric),
    ('penale_km',0.00::numeric),
    ('carburante',1697.43::numeric),
    ('autostrada',647.19::numeric),
    ('bollo',340.97::numeric),
    ('assicurazione',1060.86::numeric),
    ('manutenzione_auto',865.36::numeric),
    ('commercialista',1880.80::numeric),
    ('gestionale',36.48::numeric),
    ('pc',0.00::numeric),
    ('telefono_tablet',0.00::numeric)
  ) as x(code,amount)
  join public.cost_categories c
    on c.fiscal_year_id=y2026 and c.code=x.code;

  -- Spese mensili già presenti nel foglio. Il giorno 01 è un riferimento
  -- tecnico perché il file contiene il mese, non la data del documento.
  insert into public.costs
    (fiscal_year_id,category_id,vehicle_id,expense_date,description,
     gross_amount,amount_includes_vat,vat_rate,vat_deductible_rate,
     cost_deductible_rate,fiscal_competence_year,notes)
  select
    y2026,c.id,v_id,x.giorno,x.descrizione,x.importo,false,0,0,0,2026,
    'IMPORTATO DA FILE 2026 · giorno 01 tecnico'
  from (values
    ('carburante','2026-01-01'::date,'Carburante · gennaio',73.80::numeric),
    ('carburante','2026-02-01'::date,'Carburante · febbraio',199.45::numeric),
    ('carburante','2026-03-01'::date,'Carburante · marzo',159.09::numeric),
    ('carburante','2026-04-01'::date,'Carburante · aprile',217.19::numeric),
    ('carburante','2026-05-01'::date,'Carburante · maggio',164.59::numeric),
    ('carburante','2026-06-01'::date,'Carburante · giugno',47.37::numeric),
    ('carburante','2026-07-01'::date,'Carburante · luglio',219.58::numeric),
    ('carburante','2026-08-01'::date,'Carburante · agosto',19.78::numeric),
    ('carburante','2026-09-01'::date,'Carburante · settembre',172.22::numeric),

    ('autostrada','2026-01-01'::date,'Autostrada · gennaio',0.00::numeric),
    ('autostrada','2026-02-01'::date,'Autostrada · febbraio',51.40::numeric),
    ('autostrada','2026-03-01'::date,'Autostrada · marzo',57.73::numeric),
    ('autostrada','2026-04-01'::date,'Autostrada · aprile',43.24::numeric),
    ('autostrada','2026-05-01'::date,'Autostrada · maggio',97.00::numeric),
    ('autostrada','2026-06-01'::date,'Autostrada · giugno',35.90::numeric),
    ('autostrada','2026-07-01'::date,'Autostrada · luglio',70.52::numeric),
    ('autostrada','2026-08-01'::date,'Autostrada · agosto',32.90::numeric),
    ('autostrada','2026-09-01'::date,'Autostrada · settembre',96.70::numeric),

    ('rate_auto','2026-01-01'::date,'Rata auto · gennaio',0.00::numeric),
    ('rate_auto','2026-02-01'::date,'Rata auto · febbraio',0.00::numeric),
    ('rate_auto','2026-03-01'::date,'Rata auto · marzo',663.16::numeric),
    ('rate_auto','2026-04-01'::date,'Rata auto · aprile',663.73::numeric),
    ('rate_auto','2026-05-01'::date,'Rata auto · maggio',664.60::numeric),
    ('rate_auto','2026-06-01'::date,'Rata auto · giugno',664.91::numeric),
    ('rate_auto','2026-07-01'::date,'Rata auto · luglio',661.69::numeric),
    ('rate_auto','2026-08-01'::date,'Rata auto · agosto',668.15::numeric),
    ('rate_auto','2026-09-01'::date,'Rata auto · settembre',667.88::numeric)
  ) as x(code,giorno,descrizione,importo)
  join public.cost_categories c
    on c.fiscal_year_id=y2026 and c.code=x.code;

  -- Parametri del modello Excel 2026.
  insert into public.fiscal_parameters
    (fiscal_year_id,code,description,value,unit,source,is_provisional)
  values
    (y2026,'forfettario_coeff_redditivita','Coefficiente di redditività',0.62,'RATE','IMPORTATO DA FILE 2026',false),
    (y2026,'forfettario_aliquota_sostitutiva','Aliquota imposta sostitutiva',0.15,'RATE','IMPORTATO DA FILE 2026',false),
    (y2026,'forfettario_limite_ragguagliato','Limite 85.000 € ragguagliato usato nel file',82205,'EUR','IMPORTATO DA FILE 2026',true),
    (y2026,'forfettario_limite_uscita_immediata','Limite uscita immediata',100000,'EUR','IMPORTATO DA FILE 2026',false),
    (y2026,'forfettario_mesi_proiezione','Numero mesi usati dalla proiezione del file',11,'EUR','IMPORTATO DA FILE 2026',true),
    (y2026,'forfettario_contributi_ap','Contributi anni precedenti nel file',0,'EUR','IMPORTATO DA FILE 2026',false),
    (y2026,'forfettario_riduzione_inps','Scenario riduzione INPS del file',0.35,'RATE','IMPORTATO DA FILE 2026 · confronto da verificare',true),
    (y2026,'inps_fisso_foglio','INPS fisso del file',3031.76,'EUR','IMPORTATO DA FILE 2026',true),
    (y2026,'inps_minimale_foglio','Minimale INPS del file',18808.01,'EUR','IMPORTATO DA FILE 2026',true),
    (y2026,'inps_aliquota_prima_foglio','Aliquota INPS prima fascia',0.2448,'RATE','IMPORTATO DA FILE 2026',true),
    (y2026,'inps_soglia_seconda_foglio','Soglia seconda fascia INPS',56224,'EUR','IMPORTATO DA FILE 2026',true),
    (y2026,'inps_aliquota_seconda_foglio','Aliquota INPS seconda fascia',0.2548,'RATE','IMPORTATO DA FILE 2026',true),
    (y2026,'enasarco_tasso_foglio','Quota personale Enasarco',0.085,'RATE','IMPORTATO DA FILE 2026',true),
    (y2026,'enasarco_massimale_pluri','Massimale Enasarco plurimandatario',30478,'EUR','IMPORTATO DA FILE 2026',true),
    (y2026,'enasarco_massimale_mono','Massimale Enasarco monomandatario',45717,'EUR','IMPORTATO DA FILE 2026',true);

end $$;

notify pgrst, 'reload schema';

-- Riepilogo visivo: deve mostrare fatturato 78.816,98 € e 8 mesi compilati.
select 'Anno fiscale' as voce,
       concat(f.fiscal_year,' · ',f.status) as valore
from public.fiscal_years f
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=f.id
union all
select 'Fatturato registrato',
       to_char(sum(r.amount),'FM999999999990D00')
from public.monthly_revenues r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Mesi fatturato compilati',
       count(distinct r.month)::text
from public.monthly_revenues r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Righe fatturato',
       count(*)::text
from public.monthly_revenues r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Provvigioni nette · righe',
       count(*)::text
from public.monthly_net_commissions r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Accantonamenti · righe',
       count(*)::text
from public.monthly_reserves r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Percorrenza · righe',
       count(*)::text
from public.vehicle_monthly r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Costi mensili · righe',
       count(*)::text
from public.costs r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Stime costi annuali · righe',
       count(*)::text
from public.annual_cost_estimates r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id
union all
select 'Parametri forfettario/INPS/Enasarco',
       count(*)::text
from public.fiscal_parameters r
join pg_temp.piva_import_2026_context c on c.fiscal_year_id=r.fiscal_year_id;

commit;
