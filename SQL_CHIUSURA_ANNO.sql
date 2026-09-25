-- ABILITA CHIUSURA / RIAPERTURA ANNO FISCALE
-- Eseguire SOLO nel Supabase del Gestionale Partita IVA.
-- Non usare nei progetti Gestionale Ordini o Gestionale Prospect.
--
-- Consente all'utente autenticato di modificare SOLO lo stato del proprio anno:
--   open -> closed
--   closed -> open
-- id, user_id e fiscal_year restano immutabili.
--
-- Prima di Run sostituire DA_CONFERMARE con CONFERMO_CHIUSURA_ANNO.

begin;
set local app.confirm_fiscal_year_status = 'DA_CONFERMARE';

do $$
begin
  if current_setting('app.confirm_fiscal_year_status', true)
       is distinct from 'CONFERMO_CHIUSURA_ANNO' then
    raise exception
      'Script bloccato: verifica il progetto Partita IVA e sostituisci DA_CONFERMARE con CONFERMO_CHIUSURA_ANNO';
  end if;

  if to_regclass('public.fiscal_years') is null then
    raise exception 'Tabella public.fiscal_years assente';
  end if;

  if not exists (
       select 1 from information_schema.columns
       where table_schema='public' and table_name='fiscal_years' and column_name='id'
     )
     or not exists (
       select 1 from information_schema.columns
       where table_schema='public' and table_name='fiscal_years' and column_name='user_id'
     )
     or not exists (
       select 1 from information_schema.columns
       where table_schema='public' and table_name='fiscal_years' and column_name='fiscal_year'
     )
     or not exists (
       select 1 from information_schema.columns
       where table_schema='public' and table_name='fiscal_years' and column_name='status'
     ) then
    raise exception 'Schema fiscal_years non compatibile';
  end if;
end $$;

alter table public.fiscal_years enable row level security;

-- L'app deve poter inviare UPDATE; il trigger sottostante impedisce comunque
-- modifiche a id, user_id e fiscal_year.
grant select, update on table public.fiscal_years to authenticated;

create or replace function public.piva_validate_fiscal_year_status()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  if new.id is distinct from old.id
     or new.user_id is distinct from old.user_id
     or new.fiscal_year is distinct from old.fiscal_year then
    raise exception 'Per un anno fiscale è modificabile soltanto lo stato';
  end if;

  if old.status not in ('open','closed')
     or new.status not in ('open','closed') then
    raise exception 'Stato anno fiscale non valido';
  end if;

  if new.status = old.status then
    return new;
  end if;

  if not (
       (old.status='open' and new.status='closed')
       or (old.status='closed' and new.status='open')
     ) then
    raise exception 'Transizione stato anno fiscale non consentita';
  end if;

  return new;
end $$;

revoke all on function public.piva_validate_fiscal_year_status()
from public, anon, authenticated;

drop trigger if exists piva_validate_fiscal_year_status
on public.fiscal_years;

create trigger piva_validate_fiscal_year_status
before update on public.fiscal_years
for each row
execute function public.piva_validate_fiscal_year_status();

-- Policy permissiva necessaria per l'UPDATE del proprio anno.
drop policy if exists piva_fiscal_year_update_owner
on public.fiscal_years;

create policy piva_fiscal_year_update_owner
on public.fiscal_years
for update
to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

-- Guardia restrittiva: anche in presenza di eventuali policy legacy più ampie,
-- una riga altrui non può essere aggiornata.
drop policy if exists piva_fiscal_year_update_owner_guard
on public.fiscal_years;

create policy piva_fiscal_year_update_owner_guard
on public.fiscal_years
as restrictive
for update
to authenticated
using (user_id = (select auth.uid()))
with check (user_id = (select auth.uid()));

notify pgrst, 'reload schema';
commit;

-- Verifica facoltativa:
-- select fiscal_year, status from public.fiscal_years order by fiscal_year;
