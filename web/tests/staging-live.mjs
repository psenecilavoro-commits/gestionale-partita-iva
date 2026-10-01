// Run explicitly; test credentials are local and never committed.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createClient} from '@supabase/supabase-js';
import {readTable,applyMutations} from '../src/data.js';
const users=JSON.parse(fs.readFileSync('.staging-test-users.json'));
const url='https://gbtvscldenpmvcvwognw.supabase.co';
const key='sb_publishable_5lyEqt6VE7BLi8JNA7-dcw_1ZQz0EcV';
const clients=users.map(()=>createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}}));
for(let i=0;i<2;i++){
 const {error}=await clients[i].auth.signInWithPassword(users[i]);
 assert.equal(error,null,error?.message);
 const {data}=await clients[i].auth.getUser();assert.equal(data.user.id,users[i].id);
}
const first=clients[0],second=clients[1];
const {data:years,error}=await first.from('fiscal_years').select('*');assert.equal(error,null);
let year=years.find(y=>y.fiscal_year===2026);
if(!year){const r=await first.from('fiscal_years').insert({fiscal_year:2026}).select().single();assert.equal(r.error,null,r.error?.message);year=r.data;}
assert.equal((await readTable(second,'fiscal_years')).length,0);
const blocked=await second.from('fiscal_years').insert({user_id:users[0].id,fiscal_year:2027});assert.ok(blocked.error);
await applyMutations(first,[{table:'fiscal_years',operation:'update',payload:{status:'closed'},filters:[['id',year.id]],expected_rows:1}]);
assert.equal((await readTable(first,'fiscal_years')).find(y=>y.id===year.id).status,'closed');
await applyMutations(first,[{table:'fiscal_years',operation:'update',payload:{status:'open'},filters:[['id',year.id]],expected_rows:1}]);
const principal=(await readTable(first,'principals'))[0];
if(principal){
 const sales=await first.from('sales_vat_invoices').insert({fiscal_year_id:year.id,principal_id:principal.id,invoice_number:'COLLAUDO-'+Date.now(),invoice_date:'2026-01-10',vat_month:1,document_type:'fattura',taxable_amount:100,vat_amount:22}).select().single();assert.equal(sales.error,null,sales.error?.message);
 assert.equal((await readTable(second,'sales_vat_invoices')).length,0);
 const id=sales.data.id;
 await applyMutations(first,[{table:'sales_vat_invoices',operation:'update',payload:{taxable_amount:120},filters:[['id',id],['version',1]],expected_rows:1}]);
 await assert.rejects(applyMutations(first,[{table:'sales_vat_invoices',operation:'update',payload:{taxable_amount:130},filters:[['id',id],['version',1]],expected_rows:1}]),/Salvataggio non confermato/);
 assert.equal((await readTable(first,'sales_vat_invoices')).find(r=>r.id===id).version,2);
 await first.from('fiscal_years').update({status:'closed'}).eq('id',year.id);
 const denied=await first.from('sales_vat_invoices').update({taxable_amount:140}).eq('id',id).select();assert.ok(denied.error||denied.data.length===0);
 await first.from('fiscal_years').update({status:'open'}).eq('id',year.id);
 assert.equal((await first.from('sales_vat_invoices').delete().eq('id',id)).error,null);
 const pension=await first.from('pension_payments').insert({fiscal_year_id:year.id,description:'COLLAUDO temporaneo',payment_date:'2026-01-10',amount:100}).select().single();assert.equal(pension.error,null,pension.error?.message);
 assert.equal((await first.from('pension_payments').delete().eq('id',pension.data.id)).error,null);
 const period={fiscal_year_id:year.id,frequency:'mensile',month_from:1,month_to:1,opening_credit:0,adjustment:0,interest_amount:0,paid_amount:0,documents_complete:false};
 const vat=await first.from('vat_periods').insert(period).select().single();assert.equal(vat.error,null,vat.error?.message);
 assert.ok((await first.from('vat_periods').insert(period)).error);
 assert.equal((await first.from('vat_periods').delete().eq('id',vat.data.id)).error,null);
 console.log('PASS: VAT owner isolation, optimistic version conflict, closed-year write denial, pension registration, overlapping VAT periods rejected');
}
const anon=createClient(url,key,{auth:{persistSession:false}});
const publicRead=await anon.from('fiscal_years').select('*');assert.ok(publicRead.error||publicRead.data.length===0);
for(const client of clients)assert.equal((await client.auth.signOut()).error,null);
console.log('PASS: real Auth password/JWT, owner isolation, blocked cross-owner insert, close/reopen via transport, anonymous protection, logout');
