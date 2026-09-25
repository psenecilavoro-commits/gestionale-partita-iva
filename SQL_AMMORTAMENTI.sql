-- Eseguire SOLO nel Supabase del Gestionale Partita IVA (secondo account).
-- Tabella globale per i beni: fiscal_year_id identifica l'anno di acquisto;
-- le quote restano visibili negli anni successivi senza duplicare il bene.
begin;

create table if not exists public.depreciable_assets (
  id uuid primary key default gen_random_uuid(),
  fiscal_year_id uuid not null references public.fiscal_years(id) on delete restrict,
  description text not null check (length(btrim(description)) between 1 and 200),
  purchase_date date not null check (purchase_date <= current_date),
  gross_amount numeric(14,2) not null check (gross_amount >= 0),
  deductible_vat numeric(14,2) not null check (deductible_vat >= 0 and deductible_vat <= gross_amount),
  depreciation_rate numeric(9,6) not null check (depreciation_rate > 0 and depreciation_rate <= 1),
  first_fiscal_year integer not null check (first_fiscal_year between 2000 and 2100),
  notes text check (notes is null or length(notes) <= 500),
  version integer not null default 1
);

alter table public.depreciable_assets enable row level security;
revoke all on table public.depreciable_assets from public, anon, authenticated;
grant select, insert, update, delete on table public.depreciable_assets to authenticated;
create index if not exists depreciable_assets_year_idx on public.depreciable_assets(fiscal_year_id);

create or replace function public.piva_validate_depreciable_asset()
returns trigger language plpgsql security invoker set search_path='' as $$
declare fy public.fiscal_years%rowtype;
begin
  select * into fy from public.fiscal_years where id=new.fiscal_year_id;
  if fy.id is null or fy.user_id is distinct from auth.uid() or fy.status <> 'open' then
    raise exception 'Anno di acquisto non accessibile o chiuso';
  end if;
  if extract(year from new.purchase_date) <> fy.fiscal_year
     or new.first_fiscal_year <> fy.fiscal_year then
    raise exception 'Data/anno del bene non coerenti con anno di acquisto';
  end if;
  if tg_op='UPDATE' then
    if new.fiscal_year_id is distinct from old.fiscal_year_id then
      raise exception 'Spostamento tra anni non consentito';
    end if;
    new.version:=old.version+1;
  end if;
  return new;
end $$;
revoke all on function public.piva_validate_depreciable_asset() from public,anon,authenticated;

drop trigger if exists piva_validate_depreciable_asset on public.depreciable_assets;
create trigger piva_validate_depreciable_asset
before insert or update on public.depreciable_assets
for each row execute function public.piva_validate_depreciable_asset();

drop policy if exists piva_depreciable_read on public.depreciable_assets;
create policy piva_depreciable_read on public.depreciable_assets for select to authenticated
using (exists(select 1 from public.fiscal_years f
             where f.id=fiscal_year_id and f.user_id=(select auth.uid())));

drop policy if exists piva_depreciable_insert on public.depreciable_assets;
create policy piva_depreciable_insert on public.depreciable_assets for insert to authenticated
with check (exists(select 1 from public.fiscal_years f
                  where f.id=fiscal_year_id and f.user_id=(select auth.uid()) and f.status='open'));

drop policy if exists piva_depreciable_update on public.depreciable_assets;
create policy piva_depreciable_update on public.depreciable_assets for update to authenticated
using (exists(select 1 from public.fiscal_years f
             where f.id=fiscal_year_id and f.user_id=(select auth.uid()) and f.status='open'))
with check (exists(select 1 from public.fiscal_years f
                  where f.id=fiscal_year_id and f.user_id=(select auth.uid()) and f.status='open'));

drop policy if exists piva_depreciable_delete on public.depreciable_assets;
create policy piva_depreciable_delete on public.depreciable_assets for delete to authenticated
using (exists(select 1 from public.fiscal_years f
             where f.id=fiscal_year_id and f.user_id=(select auth.uid()) and f.status='open'));

notify pgrst,'reload schema';
commit;
