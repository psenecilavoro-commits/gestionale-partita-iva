"""Test soltanto nel PostgreSQL temporaneo della CI, mai nel Supabase reale."""
import os
import subprocess
from pathlib import Path

if (os.environ.get("PIVA_SQL_TEST") != "temporary-ci-database"
        or os.environ.get("PGDATABASE") != "piva_test"
        or os.environ.get("PGHOST") not in ("127.0.0.1", "localhost")):
    raise SystemExit("Consentito solo sul database temporaneo locale piva_test della CI")


def sql(testo, ok=True):
    r = subprocess.run(["psql", "-X", "-v", "ON_ERROR_STOP=1", "-At"], input=testo, text=True, capture_output=True)
    if (r.returncode == 0) != ok:
        raise AssertionError(f"Esito SQL inatteso: {r.stdout}\n{r.stderr}")
    return r.stdout.strip()


A = "00000000-0000-0000-0000-000000000001"
B = "00000000-0000-0000-0000-000000000002"
YA = "10000000-0000-0000-0000-000000000001"
YB = "10000000-0000-0000-0000-000000000002"
YC = "10000000-0000-0000-0000-000000000003"
YD = "10000000-0000-0000-0000-000000000004"


def user(query, who=A, ok=True):
    return sql(f"set role authenticated; set request.jwt.claim.sub = '{who}'; {query}", ok)


sql(f"""
create role anon;
create role authenticated;
create schema auth;
create function auth.uid() returns uuid language sql stable as
$$ select nullif(current_setting('request.jwt.claim.sub', true),'')::uuid $$;
grant usage on schema public, auth to authenticated, anon;
create table public.fiscal_years(id uuid primary key, user_id uuid not null, fiscal_year int, status text);
insert into public.fiscal_years values
('{YA}','{A}',extract(year from current_date),'open'),
('{YB}','{B}',extract(year from current_date),'open'),
('{YC}','{A}',extract(year from current_date),'closed'),
('{YD}','{A}',2027,'open');
alter table public.fiscal_years enable row level security;
create policy owner on public.fiscal_years to authenticated using (user_id = auth.uid());
grant select on public.fiscal_years to authenticated;
create table public.principals(id uuid primary key, user_id uuid not null);
insert into public.principals values ('40000000-0000-0000-0000-000000000001','{A}'), ('40000000-0000-0000-0000-000000000002','{B}');
grant select on public.principals to authenticated;
create table public.monthly_revenues(id uuid primary key);
create table public.tax_deductions(id uuid primary key);
create table public.costs(id uuid primary key, fiscal_year_id uuid references public.fiscal_years(id));
create table public.purchase_vat_invoices(id uuid primary key, fiscal_year_id uuid references public.fiscal_years(id));
alter table public.costs enable row level security;
alter table public.purchase_vat_invoices enable row level security;
create policy owner on public.costs to authenticated using (exists(select 1 from public.fiscal_years f where f.id = fiscal_year_id));
create policy owner on public.purchase_vat_invoices to authenticated using (exists(select 1 from public.fiscal_years f where f.id = fiscal_year_id));
grant select on public.costs, public.purchase_vat_invoices to authenticated;
insert into public.costs values ('20000000-0000-0000-0000-000000000001','{YA}'), ('20000000-0000-0000-0000-000000000002','{YB}');
insert into public.purchase_vat_invoices values ('30000000-0000-0000-0000-000000000001','{YA}');
""")
sql((Path(__file__).parents[1] / "SQL_IVA_VENDITE.sql").read_text(encoding="utf-8"))
user(f"insert into public.sales_vat_invoices(fiscal_year_id,principal_id,invoice_number,invoice_date,document_type,taxable_amount,vat_amount) values('{YA}','40000000-0000-0000-0000-000000000001','LEGACY',current_date,'fattura',100,22)")
migrazione = (Path(__file__).parents[1] / "SQL_COMPLETAMENTO_STRUTTURA.sql").read_text(encoding="utf-8")
sql(migrazione, ok=False)
migrazione = migrazione.replace("= 'DA_CONFERMARE'", "= 'CONFERMO_SOLO_PARTITA_IVA'")
sql(migrazione)
sql(migrazione)
assert user("select taxable_amount = 100 and vat_amount = 22 and vat_month is null from public.sales_vat_invoices where invoice_number='LEGACY'").endswith("t")
sql("delete from public.sales_vat_invoices where invoice_number='LEGACY'")

insert_sale = """insert into public.sales_vat_invoices
(fiscal_year_id,principal_id,invoice_number,invoice_date,vat_month,document_type,taxable_amount,vat_amount)
values ('%s','40000000-0000-0000-0000-000000000001','%s',current_date,1,'fattura',100,22)"""
user(insert_sale % (YA, "1"))
user(insert_sale % (YA, "1"), ok=False)
user(insert_sale % (YB, "2"), ok=False)
user(insert_sale % (YC, "3"), ok=False)
assert user("select count(*) from public.sales_vat_invoices", B).endswith("0")
assert user("update public.sales_vat_invoices set vat_amount=999 returning id", B).endswith("UPDATE 0")
user("update public.sales_vat_invoices set vat_amount=23 where version=1")
assert user("select version from public.sales_vat_invoices").endswith("2")
assert user("update public.sales_vat_invoices set vat_amount=24 where version=1 returning id").endswith("UPDATE 0")
period = f"""insert into public.vat_periods(fiscal_year_id,frequency,month_from,month_to,opening_credit,adjustment,interest_amount,paid_amount)
values('{YA}','mensile',1,1,0,0,0,0)"""
user(period)
user(period, ok=False)
user(f"insert into public.pension_payments(fiscal_year_id,description,payment_date,amount) values('{YA}','Pensione',current_date,100)")
user(f"insert into public.purchase_cost_links(fiscal_year_id,purchase_id,cost_id) values('{YA}','30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000002')", ok=False)
user(f"insert into public.purchase_cost_links(fiscal_year_id,purchase_id,cost_id) values('{YA}','30000000-0000-0000-0000-000000000001','20000000-0000-0000-0000-000000000001')")
for table in ("sales_vat_invoices", "vat_periods", "pension_payments", "purchase_cost_links"):
    assert user(f"select count(*) from public.{table}", B).endswith("0")
    assert user(f"delete from public.{table} returning id", B).endswith("DELETE 0")
    sql(f"set role anon; select * from public.{table}", ok=False)

ammortamenti = (Path(__file__).parents[1] / "SQL_AMMORTAMENTI.sql").read_text(encoding="utf-8")
sql(ammortamenti)
sql(ammortamenti)
user(f"""insert into public.depreciable_assets
(fiscal_year_id,description,purchase_date,gross_amount,deductible_vat,depreciation_rate,first_fiscal_year,is_planned)
values('{YA}','Bene previsto',current_date,500,0,1,extract(year from current_date),true)""")
assert user("select is_planned from public.depreciable_assets where description='Bene previsto'").endswith("t")
assert user("select count(*) from public.depreciable_assets", B).endswith("0")
sql("set role anon; select * from public.depreciable_assets", ok=False)

# Reset operativo 2027: deve cancellare i dati annuali e conservare la riga dell'anno.
sql(f"insert into public.costs values ('20000000-0000-0000-0000-000000000003','{YD}')")
sql(f"insert into public.purchase_vat_invoices values ('30000000-0000-0000-0000-000000000002','{YD}')")
reset = (Path(__file__).parents[1] / "SQL_RESET_OPERATIVO_2027.sql").read_text(encoding="utf-8")
reset = reset.replace("= 'DA_CONFERMARE'", "= 'CONFERMO_RESET_2027'")
sql(reset)
assert sql(f"select count(*) from public.fiscal_years where id='{YD}' and fiscal_year=2027 and status='open'").endswith("1")
assert sql(f"select count(*) from public.costs where fiscal_year_id='{YD}'").endswith("0")
assert sql(f"select count(*) from public.purchase_vat_invoices where fiscal_year_id='{YD}'").endswith("0")

sql(f"update public.fiscal_years set status='closed' where id='{YA}'")
for table in ("sales_vat_invoices", "vat_periods", "pension_payments", "purchase_cost_links"):
    assert user(f"delete from public.{table} returning id").endswith("DELETE 0")
    assert user(f"update public.{table} set version=99 returning id").endswith("UPDATE 0")

# Import 2026: prova in un nuovo schema minimale e isolato.
sql("""
drop schema public cascade;
create schema public;
create table public.fiscal_years(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  fiscal_year integer not null,
  status text not null
);
create table public.principals(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  name text not null,
  enasarco_relationship text not null,
  active boolean not null default true
);
create table public.monthly_revenues(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  principal_id uuid not null references public.principals(id),
  month integer not null,
  amount numeric(14,2) not null,
  notes text
);
create table public.monthly_reserves(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  month integer not null,
  reserved_amount numeric(14,2) not null,
  notes text
);
create table public.monthly_net_commissions(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  month integer not null,
  amount numeric(14,2) not null
);
create table public.vehicles(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  label text not null,
  notes text
);
create table public.vehicle_monthly(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  vehicle_id uuid not null references public.vehicles(id),
  month integer not null,
  distance_km numeric(14,2) not null,
  notes text
);
create table public.vehicle_year_settings(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  vehicle_id uuid not null references public.vehicles(id),
  annual_km_limit integer,
  excess_km_penalty numeric(14,2),
  notes text
);
create table public.cost_categories(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  code text not null,
  name text not null,
  vat_rate numeric(9,6) not null,
  vat_deductible_rate numeric(9,6) not null,
  cost_deductible_rate numeric(9,6) not null,
  deductible_limit numeric(14,2),
  notes text
);
create table public.annual_cost_estimates(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  category_id uuid not null references public.cost_categories(id),
  estimated_gross_amount numeric(14,2) not null,
  amount_includes_vat boolean not null,
  notes text
);
create table public.costs(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  category_id uuid not null references public.cost_categories(id),
  vehicle_id uuid references public.vehicles(id),
  expense_date date not null,
  description text not null,
  gross_amount numeric(14,2) not null check (gross_amount >= 0),
  amount_includes_vat boolean not null,
  vat_rate numeric(9,6) not null,
  vat_deductible_rate numeric(9,6) not null,
  cost_deductible_rate numeric(9,6) not null,
  fiscal_competence_year integer not null,
  notes text
);
create table public.fiscal_parameters(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid(),
  fiscal_year_id uuid not null references public.fiscal_years(id),
  code text not null,
  description text not null,
  value numeric(18,6) not null,
  unit text not null,
  source text,
  source_date date,
  is_provisional boolean not null default true
);
insert into public.fiscal_years(user_id,fiscal_year,status)
values ('00000000-0000-0000-0000-000000000001',2027,'open');
""")
import_2026 = (Path(__file__).parents[1] / "SQL_IMPORTA_2026_FORFETTARIO.sql").read_text(encoding="utf-8")
sql(import_2026, ok=False)
import_2026 = import_2026.replace("= 'DA_CONFERMARE'", "= 'CONFERMO_IMPORT_2026'")
sql(import_2026)
assert sql("select count(*) from public.fiscal_years where fiscal_year=2026 and status='open'").endswith("1")
assert sql("select sum(amount) from public.monthly_revenues r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("78816.98")
assert sql("select count(*) from public.monthly_revenues r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026 and r.user_id='00000000-0000-0000-0000-000000000001'").endswith("32")
assert sql("select count(distinct month) from public.monthly_revenues r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("8")
assert sql("select count(*) from public.monthly_revenues r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("32")
assert sql("select count(*) from public.monthly_net_commissions r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("9")
assert sql("select count(*) from public.monthly_reserves r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("9")
assert sql("select count(*) from public.vehicle_monthly r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("8")
assert sql("select count(*) from public.costs r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("27")
assert sql("select count(*) from public.annual_cost_estimates r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("11")
assert sql("select count(*) from public.fiscal_parameters r join public.fiscal_years f on f.id=r.fiscal_year_id where f.fiscal_year=2026").endswith("15")
assert sql("select count(*) from public.fiscal_years where fiscal_year=2027 and status='open'").endswith("1")
sql(import_2026, ok=False)

print("SQL OK: guardia, idempotenza, RLS, anno chiuso, versioni, duplicati, collegamenti, ammortamenti, reset 2027 e import 2026.")
