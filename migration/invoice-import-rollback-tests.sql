select set_config('request.jwt.claim.sub',(select user_id::text from public.fiscal_years limit 1),true);
set local role authenticated;
do $test$
declare u uuid:=auth.uid(); fy uuid:=gen_random_uuid(); cat uuid:=gen_random_uuid(); pr uuid; p jsonb; import_id uuid; n int; failed bool; prev numeric;
begin
 insert into public.fiscal_years(id,fiscal_year,status,notes) values(fy,2025,'open','TEMPORARY ROLLBACK TEST');
 insert into public.cost_categories(id,fiscal_year_id,code,name,vat_rate,vat_deductible_rate,cost_deductible_rate)
 values(cat,fy,'commercialista','TEMPORARY ROLLBACK TEST',.22,1,1);
 select principals.id into pr from public.principals where user_id=u limit 1;
 p:=jsonb_build_object('direction','ricevuta','invoice_number','TEST-IMPORT','invoice_date','2025-09-05','payment_date','2025-09-08','subject','TEST SUPPLIER','tax_id','TESTVAT','total','667.88','base','556.34','vat','111.54','economic_year_id',fy,'document_year_id',fy,'vat_year_id',fy,'category_id',cat,'received_date','2025-09-07','registered_date','2025-09-08','deductible_vat','111.54','vat_category','altro','groups',jsonb_build_array(jsonb_build_object('base','506.99','vat','111.54','rate','22','nature','','payability','I'),jsonb_build_object('base','49.35','vat','0.00','rate','0','nature','N1','payability','I')));
 import_id:=public.piva_import_invoice(p);
 select count(*) into n from public.costs where fiscal_year_id=fy;
 if n<>2 or (select sum(gross_amount) from public.costs where fiscal_year_id=fy)<>667.88 then raise exception 'FAIL mixed costs'; end if;
 if (select deductible_vat from public.purchase_vat_invoices where fiscal_year_id=fy)<>111.54 then raise exception 'FAIL VAT'; end if;
 if (select jsonb_array_length(record_ids->'costs') from public.invoice_imports where invoice_number='TEST-IMPORT' limit 1) is null then raise exception 'FAIL refs'; end if;
 failed:=false;begin perform public.piva_import_invoice(p);exception when others then failed:=true;end;
 if not failed or (select count(*) from public.costs where fiscal_year_id=fy)<>2 then raise exception 'FAIL duplicate';end if;
 -- A failure after entering the RPC must roll back the aggregate and ledger together.
 p:=p||jsonb_build_object('direction','emessa','invoice_number','SALE-1','principal_id',pr,'previous_amount',null,'base','100.00','vat','22.00','total','122.00','vat_year_id',null,'groups',jsonb_build_array(jsonb_build_object('base','100.00','vat','22.00','rate','22','nature','','payability','I')));
 perform public.piva_import_invoice(p);
 if (select amount from public.monthly_revenues where fiscal_year_id=fy)<>100 then raise exception 'FAIL revenue';end if;
 failed:=false;begin perform public.piva_import_invoice(p||jsonb_build_object('invoice_number','SALE-2'));exception when others then failed:=true;end;
 if not failed or (select amount from public.monthly_revenues where fiscal_year_id=fy)<>100 then raise exception 'FAIL stale';end if;
 p:=p||jsonb_build_object('previous_amount','100.00');
 perform public.piva_import_invoice(p||jsonb_build_object('invoice_number','SALE-2'));
 if (select amount from public.monthly_revenues where fiscal_year_id=fy)<>200 then raise exception 'FAIL accumulation';end if;
 failed:=false;begin perform public.piva_import_invoice(p||jsonb_build_object('invoice_number','SALE-3','previous_amount','200.00','total','999'));exception when others then failed:=true;end;
 if not failed or (select amount from public.monthly_revenues where fiscal_year_id=fy)<>200 then raise exception 'FAIL validation rollback';end if;
 update public.fiscal_years set status='closed' where id=fy;
 failed:=false;begin perform public.piva_import_invoice(p||jsonb_build_object('invoice_number','SALE-CLOSED','previous_amount','200.00'));exception when others then failed:=true;end;
 if not failed then raise exception 'FAIL closed';end if;
end $test$;
select set_config('request.jwt.claim.sub','ffffffff-ffff-ffff-ffff-ffffffffffff',true);
do $security$
declare failed bool:=false;
begin
 if exists(select 1 from public.invoice_imports) then raise exception 'FAIL RLS isolation';end if;
 begin perform public.piva_import_invoice('{}'::jsonb);exception when others then failed:=true;end;
 if not failed then raise exception 'FAIL unauthorized import';end if;
end $security$;
reset role;
set local role anon;
do $anon$
declare failed bool:=false;
begin
 begin perform public.piva_import_invoice('{}'::jsonb);exception when insufficient_privilege then failed:=true;end;
 if not failed then raise exception 'FAIL anon execute';end if;
end $anon$;
reset role;
rollback;
select 'PASS: mixed VAT, costs, duplicate, aggregate, stale, invalid totals, closed year; all fixtures rolled back' as result;
