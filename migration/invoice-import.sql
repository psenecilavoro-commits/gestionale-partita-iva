-- Additive import registry and atomic RPC. Existing tables, formulas and policies unchanged.
begin;
create table public.invoice_imports (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null default auth.uid() references auth.users(id),
 document_key text not null check(length(document_key) between 1 and 500),
 direction text not null check(direction in ('emessa','ricevuta')),
 invoice_number text not null,
 invoice_date date not null,
 payment_date date not null,
 subject text not null,
 economic_year_id uuid not null references public.fiscal_years(id),
 document_year_id uuid not null references public.fiscal_years(id),
 vat_year_id uuid references public.fiscal_years(id),
 total numeric(14,2) not null check(total>0),
 record_ids jsonb not null default '{}',
 created_at timestamptz not null default now(),
 unique(user_id,document_key)
);
alter table public.invoice_imports enable row level security;
revoke all on public.invoice_imports from public,anon,authenticated;
grant select,insert on public.invoice_imports to authenticated;
create policy invoice_import_read on public.invoice_imports for select to authenticated using(user_id=(select auth.uid()));
create policy invoice_import_insert on public.invoice_imports for insert to authenticated with check(
 user_id=(select auth.uid()) and exists(select 1 from public.fiscal_years f where f.id=economic_year_id and f.user_id=(select auth.uid()) and f.status='open')
 and exists(select 1 from public.fiscal_years f where f.id=document_year_id and f.user_id=(select auth.uid()) and f.status='open')
 and (vat_year_id is null or exists(select 1 from public.fiscal_years f where f.id=vat_year_id and f.user_id=(select auth.uid()) and f.status='open')));
create index invoice_import_year_idx on public.invoice_imports(economic_year_id);
create index invoice_import_document_year_idx on public.invoice_imports(document_year_id);
create index invoice_import_vat_year_idx on public.invoice_imports(vat_year_id);

create function public.piva_import_invoice(p jsonb) returns uuid language plpgsql security invoker set search_path='' as $$
declare
 uid uuid:=auth.uid(); imp uuid:=gen_random_uuid(); economic public.fiscal_years%rowtype; document public.fiscal_years%rowtype; vy public.fiscal_years%rowtype;
 cat public.cost_categories%rowtype; rev public.monthly_revenues%rowtype;
 d date:=(p->>'invoice_date')::date; pay date:=(p->>'payment_date')::date;
 received date; registered date; year_id uuid; rec uuid; purchase uuid; sale uuid; costs jsonb:='[]';
 b numeric:=0; v numeric:=0; total numeric:=(p->>'total')::numeric; deductible numeric;
 g jsonb; gb numeric; gv numeric; gr numeric; key text; subject text:=btrim(p->>'subject'); number text:=btrim(p->>'invoice_number');
begin
 if uid is null then raise exception 'Sessione scaduta'; end if;
 if p->>'direction' not in ('emessa','ricevuta') or subject is null or length(subject) not between 1 and 200 or number is null or length(number) not between 1 and 100 or d is null or pay is null or d>current_date or pay>current_date then raise exception 'Dati fattura non validi'; end if;
 if jsonb_typeof(p->'groups') is distinct from 'array' or jsonb_array_length(p->'groups') not between 1 and 30 then raise exception 'Riepilogo IVA mancante'; end if;
 for g in select value from jsonb_array_elements(p->'groups') loop
  gb:=(g->>'base')::numeric; gv:=(g->>'vat')::numeric; gr:=(g->>'rate')::numeric;
  if gb is null or gv is null or gr is null or gb<0 or gv<0 or gb<>round(gb,2) or gv<>round(gv,2) or gr not in (0,4,5,10,22) or coalesce(g->>'payability','I') not in ('','I') then raise exception 'Importi o esigibilita IVA non supportati'; end if;
  if (gr=0 and (coalesce(g->>'nature','')!~'^N[1-7](\.[0-9])?$' or gv<>0)) or (gr>0 and (coalesce(g->>'nature','')<>'' or abs(round(gb*gr/100,2)-gv)>0.01)) then raise exception 'IVA incoerente'; end if;
  b:=b+gb;v:=v+gv;
 end loop;
 if total is null or total<=0 or total<>round(total,2) or total<>b+v or (p->>'base')::numeric is distinct from b or (p->>'vat')::numeric is distinct from v then raise exception 'Totali incoerenti'; end if;
 -- Use the same advisory key as year closure; deterministic ordering prevents deadlocks.
 for year_id in select distinct x from unnest(array[(p->>'economic_year_id')::uuid,(p->>'document_year_id')::uuid,nullif(p->>'vat_year_id','')::uuid]) x where x is not null order by x loop
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(year_id::text,91827));
  if not exists(select 1 from public.fiscal_years f where f.id=year_id and f.user_id=uid and f.status='open') then raise exception 'Anno mancante, chiuso o non accessibile'; end if;
 end loop;
 select * into economic from public.fiscal_years where id=(p->>'economic_year_id')::uuid and user_id=uid for share;
 select * into document from public.fiscal_years where id=(p->>'document_year_id')::uuid and user_id=uid for share;
 if economic.id is null or document.id is null or economic.fiscal_year<>extract(year from pay) or document.fiscal_year<>extract(year from d) then raise exception 'Anno di destinazione errato'; end if;
 key:=concat(p->>'direction','|',coalesce(nullif(btrim(p->>'tax_id'),''),lower(subject)),'|',lower(number),'|',d::text);
 if exists(select 1 from public.invoice_imports where user_id=uid and document_key=key) then raise exception 'Fattura gia importata'; end if;
 if p->>'direction'='emessa' then
  if (document.fiscal_year=2026 and v<>0) or (document.fiscal_year<>2026 and exists(select 1 from jsonb_array_elements(p->'groups') x where (x->>'rate')::numeric<>22)) or (document.fiscal_year=2026)<>(economic.fiscal_year=2026) then raise exception 'Regime o IVA vendita non compatibili'; end if;
  if not exists(select 1 from public.principals pr where pr.id=(p->>'principal_id')::uuid and pr.user_id=uid) then raise exception 'Mandante non accessibile'; end if;
  select * into rev from public.monthly_revenues r where r.fiscal_year_id=economic.id and r.principal_id=(p->>'principal_id')::uuid and r.month=extract(month from pay) for update;
  if rev.amount is distinct from nullif(p->>'previous_amount','')::numeric then raise exception 'Fatturato cambiato: aggiorna e controlla nuovamente l’anteprima'; end if;
  if rev.id is null then
   insert into public.monthly_revenues(fiscal_year_id,principal_id,month,amount,accrual_date,received_date,notes) values(economic.id,(p->>'principal_id')::uuid,extract(month from pay),b,d,pay,'Importazione fattura '||number) returning id into rec;
  else
   -- Drop the gross-entry marker after incrementing the net aggregate; retain other notes.
   update public.monthly_revenues set amount=amount+b,notes=split_part(coalesce(notes,''),chr(10)||'[PIVA_GROSS_22_V1]',1) where id=rev.id returning id into rec;
  end if;
  if document.fiscal_year<>2026 then
   insert into public.sales_vat_invoices(fiscal_year_id,principal_id,invoice_number,invoice_date,vat_month,document_type,taxable_amount,vat_amount,notes) values(document.id,(p->>'principal_id')::uuid,number,d,extract(month from d),'fattura',b,v,'Importazione '||imp) returning id into sale;
  end if;
 else
  select * into cat from public.cost_categories where id=(p->>'category_id')::uuid and fiscal_year_id=economic.id and user_id=uid;
  if cat.id is null or cat.code in ('pc','telefono_tablet','penale_km') then raise exception 'Categoria non accessibile o richiede modulo completo'; end if;
  if cat.code in ('rate_auto','carburante','autostrada','manutenzione_auto','assicurazione','bollo') and not exists(select 1 from public.vehicles ve where ve.id=(p->>'vehicle_id')::uuid and ve.user_id=uid) then raise exception 'Auto non accessibile'; end if;
  received:=(p->>'received_date')::date;registered:=(p->>'registered_date')::date;deductible:=(p->>'deductible_vat')::numeric;
  select * into vy from public.fiscal_years where id=(p->>'vat_year_id')::uuid and user_id=uid for share;
  if received is null or registered is null or received<d or registered<received or registered>current_date or vy.id is null or vy.fiscal_year<>extract(year from registered) or deductible is null or deductible<0 or deductible>v or deductible<>round(deductible,2) or (vy.fiscal_year=2026 and deductible<>0) then raise exception 'Date o IVA detraibile non valide'; end if;
  if (p->>'vat_category') is distinct from (case when cat.code in ('rate_auto','carburante','autostrada','manutenzione_auto','assicurazione','bollo') then 'auto' else 'altro' end) then raise exception 'Categoria IVA errata'; end if;
  if exists(select 1 from public.purchase_vat_invoices pi where lower(btrim(pi.supplier))=lower(subject) and lower(btrim(pi.invoice_number))=lower(number) and pi.invoice_date=d) then raise exception 'Fattura gia presente nel registro IVA'; end if;
  for g in select value from jsonb_array_elements(p->'groups') loop
   gb:=(g->>'base')::numeric;gv:=(g->>'vat')::numeric;gr:=(g->>'rate')::numeric;
   if gb+gv>0 then
    insert into public.costs(fiscal_year_id,category_id,vehicle_id,expense_date,payment_date,description,gross_amount,amount_includes_vat,vat_rate,vat_deductible_rate,cost_deductible_rate,deductible_limit,fiscal_competence_year,notes)
    values(economic.id,cat.id,nullif(p->>'vehicle_id','')::uuid,pay,pay,left(subject||' · fattura '||number,200),gb+gv,true,case when economic.fiscal_year=2026 then 0 else gr/100 end,case when v=0 or economic.fiscal_year=2026 then 0 else deductible/v end,cat.cost_deductible_rate,cat.deductible_limit,economic.fiscal_year,'Importazione '||imp||' · IVA documento '||gv) returning id into rec;
    costs:=costs||jsonb_build_array(rec);
   end if;
  end loop;
  if vy.fiscal_year<>2026 then
   insert into public.purchase_vat_invoices(fiscal_year_id,supplier,invoice_number,invoice_date,operation_date,received_date,registered_date,vat_amount,deductible_vat,category,anticipate,notes)
   values(vy.id,subject,number,d,d,received,registered,v,deductible,p->>'vat_category',false,'Importazione '||imp) returning id into purchase;
  end if;
 end if;
 insert into public.invoice_imports(id,user_id,document_key,direction,invoice_number,invoice_date,payment_date,subject,economic_year_id,document_year_id,vat_year_id,total,record_ids)
 values(imp,uid,key,p->>'direction',number,d,pay,subject,economic.id,document.id,nullif(p->>'vat_year_id','')::uuid,total,jsonb_build_object('costs',costs,'revenue',case when p->>'direction'='emessa' then rec else null end,'purchase',purchase,'sale',sale));
 return imp;
end $$;
revoke all on function public.piva_import_invoice(jsonb) from public,anon,authenticated;
grant execute on function public.piva_import_invoice(jsonb) to authenticated;
notify pgrst,'reload schema';
commit;
