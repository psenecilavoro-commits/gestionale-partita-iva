-- ESEGUIRE SOLO nel SQL Editor del progetto Supabase GESTIONALE PARTITA IVA.
-- NON eseguire nei progetti Ordini o Prospect. Non modifica tabelle o dati preesistenti.
-- Eseguire dopo aver verificato che public.fiscal_years e public.principals esistano.
-- Il registro contiene i VALORI DOCUMENTALI e non sostituisce monthly_revenues.
create table if not exists public.sales_vat_invoices (
    id uuid primary key default gen_random_uuid(),
    fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
    principal_id uuid not null references public.principals(id) on delete restrict,
    invoice_number text not null check (length(btrim(invoice_number)) between 1 and 100),
    invoice_date date not null,
    document_type text not null check (document_type in ('fattura','nota_credito')),
    taxable_amount numeric(14,2) not null check (taxable_amount >= 0),
    vat_amount numeric(14,2) not null check (vat_amount >= 0),
    notes text check (notes is null or length(notes) <= 500),
    unique (fiscal_year_id, principal_id, invoice_number, invoice_date, document_type)
);
create index if not exists sales_vat_invoices_year_idx
    on public.sales_vat_invoices(fiscal_year_id, invoice_date);
alter table public.sales_vat_invoices enable row level security;
revoke all on table public.sales_vat_invoices from public, anon, authenticated;
grant select, insert, update, delete on table public.sales_vat_invoices to authenticated;

-- L'anno e la mandante devono appartenere entrambi all'utente autenticato.
drop policy if exists sales_vat_select_owner on public.sales_vat_invoices;
create policy sales_vat_select_owner on public.sales_vat_invoices
for select to authenticated using (
    exists (select 1 from public.fiscal_years fy
            where fy.id = fiscal_year_id and fy.user_id = (select auth.uid()))
    and exists (select 1 from public.principals p
                where p.id = principal_id and p.user_id = (select auth.uid()))
);
drop policy if exists sales_vat_insert_owner_open on public.sales_vat_invoices;
create policy sales_vat_insert_owner_open on public.sales_vat_invoices
for insert to authenticated with check (
    exists (select 1 from public.fiscal_years fy
            where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
                  and fy.status = 'open')
    and exists (select 1 from public.principals p
                where p.id = principal_id and p.user_id = (select auth.uid()))
);
drop policy if exists sales_vat_update_owner_open on public.sales_vat_invoices;
create policy sales_vat_update_owner_open on public.sales_vat_invoices
for update to authenticated using (
    exists (select 1 from public.fiscal_years fy
            where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
                  and fy.status = 'open')
    and exists (select 1 from public.principals p
                where p.id = principal_id and p.user_id = (select auth.uid()))
) with check (
    exists (select 1 from public.fiscal_years fy
            where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
                  and fy.status = 'open')
    and exists (select 1 from public.principals p
                where p.id = principal_id and p.user_id = (select auth.uid()))
);
drop policy if exists sales_vat_delete_owner_open on public.sales_vat_invoices;
create policy sales_vat_delete_owner_open on public.sales_vat_invoices
for delete to authenticated using (
    exists (select 1 from public.fiscal_years fy
            where fy.id = fiscal_year_id and fy.user_id = (select auth.uid())
                  and fy.status = 'open')
    and exists (select 1 from public.principals p
                where p.id = principal_id and p.user_id = (select auth.uid()))
);
notify pgrst, 'reload schema';
-- Controllo dopo Run: select relrowsecurity from pg_class
-- where oid = 'public.sales_vat_invoices'::regclass;
