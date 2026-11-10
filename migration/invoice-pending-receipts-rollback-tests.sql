-- Run after recovery-schema.sql and invoice-pending-receipts.sql in an isolated database.
begin;
insert into auth.users(id) values ('00000000-0000-0000-0000-000000000001');
set local role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000001',true);

do $test$
declare
    issued_year uuid;
    receipt_year uuid;
    principal_key uuid;
    invoice_id uuid;
    payload jsonb;
    rejected boolean := false;
begin
    insert into public.fiscal_years(fiscal_year,status) values(2024,'open') returning id into issued_year;
    insert into public.fiscal_years(fiscal_year,status) values(2025,'open') returning id into receipt_year;
    insert into public.principals(name) values('Mandante di prova') returning id into principal_key;
    payload := jsonb_build_object(
        'direction','emessa','pending_receipt',true,'invoice_number','TEST-PENDING',
        'invoice_date','2024-12-18','subject','Mandante di prova',
        'document_year_id',issued_year,'principal_id',principal_key,'base',100,'vat',22,'total',122,
        'groups',jsonb_build_array(jsonb_build_object('base',100,'vat',22,'rate',22))
    );
    invoice_id := public.piva_import_invoice(payload);
    if not exists (
        select 1 from public.invoice_imports
        where id=invoice_id and payment_date is null and economic_year_id is null
    ) or exists (
        select 1 from public.monthly_revenues where principal_id=principal_key
    ) then raise exception 'Pending invoice affected cash revenue'; end if;
    if (select count(*) from public.sales_vat_invoices where principal_id=principal_key
        and fiscal_year_id=issued_year and vat_month=12 and vat_amount=22) <> 1
    then raise exception 'Documentary VAT is missing'; end if;

    perform public.piva_receive_invoice(invoice_id,'2025-01-10');
    if not exists (
        select 1 from public.monthly_revenues
        where principal_id=principal_key and fiscal_year_id=receipt_year and month=1 and amount=100
    ) or not exists (
        select 1 from public.invoice_imports
        where id=invoice_id and payment_date='2025-01-10' and economic_year_id=receipt_year
        and record_ids->>'revenue' is not null
    ) then raise exception 'Cash receipt not recorded'; end if;
    begin
        perform public.piva_receive_invoice(invoice_id,'2025-01-10');
    exception when raise_exception then
        if sqlerrm <> 'Fattura già incassata' then raise; end if;
        rejected := true;
    end;
    if not rejected or (select sum(amount) from public.monthly_revenues where principal_id=principal_key) <> 100
       or (select count(*) from public.sales_vat_invoices where principal_id=principal_key) <> 1
    then raise exception 'Repeated settlement duplicated data'; end if;
end;
$test$;
rollback;
