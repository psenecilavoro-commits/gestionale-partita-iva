-- Eseguire soltanto nel SQL Editor del progetto Supabase Gestionale Partita IVA.
-- Non eseguire nei progetti Gestionale Ordini o Gestionale Prospect.
-- Nuova tabella autonoma: NON modifica costs, annual_cost_estimates,
-- monthly_revenues, monthly_net_commissions o monthly_reserves.
-- I file delle fatture NON vengono conservati in questa tabella.

create table if not exists public.purchase_vat_invoices (
    id uuid primary key default gen_random_uuid(),
    fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
    supplier text not null check (length(btrim(supplier)) between 1 and 200),
    invoice_number text not null check (length(btrim(invoice_number)) between 1 and 100),
    invoice_date date not null,
    operation_date date not null,
    received_date date not null,
    registered_date date not null,
    vat_amount numeric(14,2) not null check (vat_amount >= 0),
    deductible_vat numeric(14,2) not null check (deductible_vat >= 0 and deductible_vat <= vat_amount),
    category text not null check (category in ('auto', 'altro')),
    anticipate boolean not null default false,
    notes text check (notes is null or length(notes) <= 500),
    check (received_date >= operation_date),
    check (registered_date >= received_date)
);

create unique index if not exists purchase_vat_invoice_identity
    on public.purchase_vat_invoices (
        fiscal_year_id, lower(btrim(supplier)), lower(btrim(invoice_number)), invoice_date
    );
create index if not exists purchase_vat_invoices_fiscal_year_idx
    on public.purchase_vat_invoices(fiscal_year_id);

alter table public.purchase_vat_invoices enable row level security;
revoke all on table public.purchase_vat_invoices from public, anon, authenticated;
grant select, insert, update, delete on table public.purchase_vat_invoices to authenticated;

-- Permessi per riga sempre limitati all'anno dell'utente autenticato.
drop policy if exists "purchase_vat_select_owner" on public.purchase_vat_invoices;
create policy "purchase_vat_select_owner" on public.purchase_vat_invoices
    for select to authenticated
    using (exists (
        select 1 from public.fiscal_years fy
        where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
    ));

drop policy if exists "purchase_vat_insert_owner_open" on public.purchase_vat_invoices;
create policy "purchase_vat_insert_owner_open" on public.purchase_vat_invoices
    for insert to authenticated
    with check (exists (
        select 1 from public.fiscal_years fy
        where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
              and fy.status = 'open'
    ));

drop policy if exists "purchase_vat_update_owner_open" on public.purchase_vat_invoices;
create policy "purchase_vat_update_owner_open" on public.purchase_vat_invoices
    for update to authenticated
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

drop policy if exists "purchase_vat_delete_owner_open" on public.purchase_vat_invoices;
create policy "purchase_vat_delete_owner_open" on public.purchase_vat_invoices
    for delete to authenticated
    using (exists (
        select 1 from public.fiscal_years fy
        where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
              and fy.status = 'open'
    ));

notify pgrst, 'reload schema';

-- Verifiche di sola lettura dopo Run:
-- select relrowsecurity from pg_class where oid = 'public.purchase_vat_invoices'::regclass;
-- select count(*) from public.purchase_vat_invoices;
