create or replace function public.initialize_vehicle_cost_categories()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    if new.fiscal_year >= 2027 and new.status = 'open' then
        insert into public.cost_categories
            (user_id, fiscal_year_id, code, name, vat_rate, vat_deductible_rate, cost_deductible_rate, notes)
        select new.user_id, new.id, category.code, category.name, 0.22, 1, 0.8,
            'Parametri di confronto dal foglio; verificare prima dell''uso reale.'
        from (values ('carburante', 'Carburante'), ('autostrada', 'Autostrada'), ('rate_auto', 'Rate')) as category(code, name)
        on conflict (user_id, fiscal_year_id, code) do nothing;
    end if;
    return new;
end;
$$;

create trigger initialize_vehicle_cost_categories
after insert or update of status on public.fiscal_years
for each row execute function public.initialize_vehicle_cost_categories();

insert into public.cost_categories
    (user_id, fiscal_year_id, code, name, vat_rate, vat_deductible_rate, cost_deductible_rate, notes)
select fiscal_year.user_id, fiscal_year.id, category.code, category.name, 0.22, 1, 0.8,
    'Parametri di confronto dal foglio; verificare prima dell''uso reale.'
from public.fiscal_years as fiscal_year
cross join (values ('carburante', 'Carburante'), ('autostrada', 'Autostrada'), ('rate_auto', 'Rate')) as category(code, name)
where fiscal_year.fiscal_year >= 2027 and fiscal_year.status = 'open'
on conflict (user_id, fiscal_year_id, code) do nothing;
