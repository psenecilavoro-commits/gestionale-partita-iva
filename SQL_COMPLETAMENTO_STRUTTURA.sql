-- NON APPLICATO. Solo progetto Partita IVA del secondo account.
-- NON usare Ordini/Prospect. Prima: backup, verifica URL/ref del progetto,
-- schema base e SQL_IVA_ACQUISTI.sql. Nessun dato esistente viene aggiornato.
-- Sostituire il valore sottostante SOLO dopo aver verificato il progetto.
begin;
set local app.confirm_partita_iva = 'DA_CONFERMARE';
do $$
begin
  if current_setting('app.confirm_partita_iva') <> 'CONFERMO_SOLO_PARTITA_IVA' then
    raise exception 'Verificare il progetto Partita IVA e impostare la conferma in testa allo script';
  end if;
  if to_regclass('public.fiscal_years') is null
     or to_regclass('public.monthly_revenues') is null
     or to_regclass('public.tax_deductions') is null
     or to_regclass('public.principals') is null
     or to_regclass('public.costs') is null
     or to_regclass('public.purchase_vat_invoices') is null then
    raise exception 'Schema Partita IVA o prerequisiti mancanti';
  end if;
end $$;

create table if not exists public.sales_vat_invoices (
  id uuid primary key default gen_random_uuid(),
  fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
  principal_id uuid not null references public.principals(id) on delete restrict,
  invoice_number text not null check (length(btrim(invoice_number)) between 1 and 100),
  invoice_date date not null check (invoice_date <= current_date),
  vat_month integer check (vat_month between 1 and 12),
  document_type text not null check (document_type in ('fattura','nota_credito')),
  taxable_amount numeric(14,2) not null check (taxable_amount >= 0),
  vat_amount numeric(14,2) not null check (vat_amount >= 0),
  version integer not null default 1,
  notes text check (notes is null or length(notes) <= 500)
);
-- Compatibilità con SQL_IVA_VENDITE.sql già aggiunto su main.
-- Le date e gli importi preesistenti restano intatti. NULL = mese IVA da confermare.
alter table public.sales_vat_invoices add column if not exists vat_month integer check (vat_month between 1 and 12);
alter table public.sales_vat_invoices add column if not exists version integer not null default 1;
create unique index if not exists sales_vat_identity on public.sales_vat_invoices
 (fiscal_year_id, principal_id, lower(btrim(invoice_number)), invoice_date, document_type);

create table if not exists public.vat_periods (
  id uuid primary key default gen_random_uuid(),
  fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
  frequency text not null check (frequency in ('mensile','trimestrale')),
  month_from integer not null check (month_from between 1 and 12),
  month_to integer not null check (month_to between month_from and 12),
  opening_credit numeric(14,2) not null check (opening_credit >= 0),
  adjustment numeric(14,2) not null,
  interest_amount numeric(14,2) not null check (interest_amount >= 0),
  paid_amount numeric(14,2) not null check (paid_amount >= 0),
  payment_date date,
  documents_complete boolean not null default false,
  version integer not null default 1,
  check ((frequency = 'mensile' and month_from = month_to) or
         (frequency = 'trimestrale' and month_from in (1,4,7,10) and month_to = month_from + 2)),
  check ((paid_amount = 0 and payment_date is null) or
         (paid_amount > 0 and payment_date is not null and payment_date <= current_date))
);

create table if not exists public.pension_payments (
  id uuid primary key default gen_random_uuid(),
  fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
  description text not null check (length(btrim(description)) between 1 and 200),
  payment_date date not null check (payment_date <= current_date),
  amount numeric(14,2) not null check (amount > 0),
  version integer not null default 1
);
create unique index if not exists pension_payment_identity on public.pension_payments
 (fiscal_year_id, payment_date, lower(btrim(description)), amount);

create table if not exists public.purchase_cost_links (
  id uuid primary key default gen_random_uuid(),
  fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
  purchase_id uuid not null unique references public.purchase_vat_invoices(id) on delete restrict,
  cost_id uuid not null unique references public.costs(id) on delete restrict,
  version integer not null default 1
);

-- SECURITY INVOKER: visibilità e proprietà dipendono anche dalle RLS esistenti.
-- Lo schema base non viene alterato: se incompatibile, la transazione fallisce.
create or replace function public.piva_validate_structure_record()
returns trigger language plpgsql security invoker set search_path = '' as $$
declare fy public.fiscal_years%rowtype;
begin
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(new.fiscal_year_id::text, 91827));
  select * into fy from public.fiscal_years where id = new.fiscal_year_id;
  if fy.id is null or fy.user_id is distinct from auth.uid() or fy.status <> 'open' then
    raise exception 'Anno non accessibile o chiuso';
  end if;
  if tg_op = 'UPDATE' then
    if new.fiscal_year_id is distinct from old.fiscal_year_id then
      raise exception 'Spostamento tra anni non consentito';
    end if;
    new.version := old.version + 1;
  else
    new.version := 1;
  end if;
  if tg_table_name = 'sales_vat_invoices' then
    if extract(year from new.invoice_date) <> fy.fiscal_year or new.invoice_date > current_date or new.vat_month is null then
      raise exception 'Data documento fuori anno/futura o mese IVA da confermare';
    end if;
  elsif tg_table_name = 'pension_payments' then
    if extract(year from new.payment_date) <> fy.fiscal_year then
      raise exception 'Pagamento pensione fuori anno';
    end if;
  elsif tg_table_name = 'vat_periods' then
    -- Lock transazionale per anno: non richiede UPDATE sulla tabella fiscal_years.
    if exists (select 1 from public.vat_periods p where p.fiscal_year_id = new.fiscal_year_id
               and p.id <> new.id and p.month_from <= new.month_to and p.month_to >= new.month_from) then
      raise exception 'Periodi sovrapposti' using errcode = '23P01';
    end if;
  elsif tg_table_name = 'purchase_cost_links' then
    if not exists (select 1 from public.purchase_vat_invoices p
                   where p.id = new.purchase_id and p.fiscal_year_id = new.fiscal_year_id)
       or not exists (select 1 from public.costs c
                      where c.id = new.cost_id and c.fiscal_year_id = new.fiscal_year_id) then
      raise exception 'Costo o fattura non visibile o appartenente a un altro anno';
    end if;
  end if;
  return new;
end $$;
revoke all on function public.piva_validate_structure_record() from public, anon, authenticated;

do $$
declare t text;
begin
  foreach t in array array['sales_vat_invoices','vat_periods','pension_payments','purchase_cost_links'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('revoke all on table public.%I from public, anon, authenticated', t);
    execute format('grant select, insert, update, delete on table public.%I to authenticated', t);
    execute format('create index if not exists %I on public.%I (fiscal_year_id)', t || '_year_idx', t);
    execute format('drop trigger if exists piva_validate_record on public.%I', t);
    execute format('create trigger piva_validate_record before insert or update on public.%I for each row execute function public.piva_validate_structure_record()', t);
    execute format('drop policy if exists piva_read on public.%I', t);
    execute format('create policy piva_read on public.%I for select to authenticated using (exists (select 1 from public.fiscal_years f where f.id = fiscal_year_id and f.user_id = (select auth.uid())))', t);
    execute format('drop policy if exists piva_insert on public.%I', t);
    execute format('create policy piva_insert on public.%I for insert to authenticated with check (exists (select 1 from public.fiscal_years f where f.id = fiscal_year_id and f.user_id = (select auth.uid()) and f.status = ''open''))', t);
    execute format('drop policy if exists piva_update on public.%I', t);
    execute format('create policy piva_update on public.%I for update to authenticated using (exists (select 1 from public.fiscal_years f where f.id = fiscal_year_id and f.user_id = (select auth.uid()) and f.status = ''open'')) with check (exists (select 1 from public.fiscal_years f where f.id = fiscal_year_id and f.user_id = (select auth.uid()) and f.status = ''open''))', t);
    execute format('drop policy if exists piva_delete on public.%I', t);
    execute format('create policy piva_delete on public.%I for delete to authenticated using (exists (select 1 from public.fiscal_years f where f.id = fiscal_year_id and f.user_id = (select auth.uid()) and f.status = ''open''))', t);
  end loop;
end $$;
-- Restrittiva: conserva il vincolo mandante anche se esistono policy legacy permissive.
drop policy if exists piva_principal_guard on public.sales_vat_invoices;
create policy piva_principal_guard on public.sales_vat_invoices as restrictive
for all to authenticated
using (exists (select 1 from public.principals p where p.id = principal_id and p.user_id = (select auth.uid())))
with check (exists (select 1 from public.principals p where p.id = principal_id and p.user_id = (select auth.uid())));
notify pgrst, 'reload schema';
commit;

-- Verifiche da eseguire separatamente con due utenti autenticati A/B e anonimo:
-- A crea un record in un proprio anno aperto; B non deve poterlo leggere,
-- modificare o cancellare. A non deve poter assegnare un anno di B.
-- Un anno chiuso deve rifiutare INSERT/UPDATE/DELETE. Ripetere per 4 tabelle.
-- Due UPDATE con lo stesso version: solo il primo deve modificare una riga.
-- Due periodi sovrapposti: il secondo deve fallire, anche da sessioni diverse.
