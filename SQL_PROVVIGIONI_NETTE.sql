-- Eseguire SOLO nel SQL Editor del progetto Supabase «Gestionale Partita IVA».
-- Aggiunge una tabella autonoma: non modifica monthly_reserves o monthly_revenues.
-- Non eseguire nel progetto Gestionale Ordini o Gestionale Prospect.

create table if not exists public.monthly_net_commissions (
    id uuid primary key default gen_random_uuid(),
    fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
    month integer not null check (month between 1 and 12),
    amount numeric(14,2) not null check (amount >= 0),
    unique (fiscal_year_id, month)
);

alter table public.monthly_net_commissions enable row level security;
revoke all on table public.monthly_net_commissions from public, anon;
grant select, insert, update, delete on table public.monthly_net_commissions to authenticated;

-- Un utente legge esclusivamente gli anni che gli appartengono.
create policy "net_commissions_select_owner"
on public.monthly_net_commissions for select to authenticated
using (exists (
    select 1 from public.fiscal_years fy
    where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
));

-- I nuovi valori si registrano solo su un anno proprio e aperto.
create policy "net_commissions_insert_owner_open"
on public.monthly_net_commissions for insert to authenticated
with check (exists (
    select 1 from public.fiscal_years fy
    where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
          and fy.status = 'open'
));

create policy "net_commissions_update_owner_open"
on public.monthly_net_commissions for update to authenticated
using (exists (
    select 1 from public.fiscal_years fy
    where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
          and fy.status = 'open'
))
with check (exists (
    select 1 from public.fiscal_years fy
    where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
          and fy.status = 'open'
));

create policy "net_commissions_delete_owner_open"
on public.monthly_net_commissions for delete to authenticated
using (exists (
    select 1 from public.fiscal_years fy
    where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
          and fy.status = 'open'
));

-- Controllo di sola lettura nel SQL Editor dopo l'esecuzione:
-- select relrowsecurity from pg_class where oid='public.monthly_net_commissions'::regclass;
-- select count(*) from public.monthly_net_commissions;
