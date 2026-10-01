// Run explicitly against disposable staging fixtures; never from automatic CI.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {createClient} from '@supabase/supabase-js';
import {applyMutations} from '../src/data.js';
const url='https://gbtvscldenpmvcvwognw.supabase.co';
assert.equal(new URL(url).hostname,'gbtvscldenpmvcvwognw.supabase.co');
const key='sb_publishable_5lyEqt6VE7BLi8JNA7-dcw_1ZQz0EcV';
const users=JSON.parse(fs.readFileSync('.staging-test-users.json'));
const clients=users.map(()=>createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}}));
for(let i=0;i<2;i++){const r=await clients[i].auth.signInWithPassword(users[i]);assert.equal(r.error,null);}
const [owner,other]=clients;
async function rows(table){const r=await owner.from(table).select('*');if(r.error)throw r.error;return r.data;}
async function roundtrip(table,payload,change,field){
 const id=randomUUID();let inserted=false;
 try{
  await applyMutations(owner,[{table,operation:'insert',payload:{id,...payload},filters:[],expected_rows:1,result_ids:[id]}]);inserted=true;
  let row=(await rows(table)).find(r=>r.id===id);assert.ok(row);assert.equal(Number(row[field]),Number(payload[field]));
  const invisible=await other.from(table).select('id').eq('id',id);assert.equal(invisible.error,null);assert.deepEqual(invisible.data,[]);
  const denied=await other.from(table).update(change).eq('id',id).select('id');assert.ok(denied.error||denied.data.length===0);
  const filters=[['id',id]];if(row.version!==undefined)filters.push(['version',row.version]);
  await applyMutations(owner,[{table,operation:'update',payload:change,filters,expected_rows:1}]);
  const updated=(await rows(table)).find(r=>r.id===id);assert.equal(Number(updated[field]),Number(change[field]));
  if(row.version!==undefined)assert.equal(updated.version,row.version+1);
  console.log('PASS:',table,'insert/update, owner isolation, cross-owner update blocked');
 }finally{
  if(inserted){await applyMutations(owner,[{table,operation:'delete',filters:[['id',id]],expected_rows:1}]);assert.ok(!(await rows(table)).some(r=>r.id===id));}
 }
}
try{
 const year=(await rows('fiscal_years')).find(r=>r.fiscal_year===2026);assert.equal(year.status,'open');
 const category=(await rows('cost_categories'))[0];const vehicle=(await rows('vehicles'))[0];
 const note='COLLAUDO AUTOMATICO TEMP '+randomUUID();
 await roundtrip('costs',{fiscal_year_id:year.id,category_id:category.id,expense_date:'2026-01-10',description:note,gross_amount:'13.50',amount_includes_vat:true,vat_rate:'0.22',vat_deductible_rate:'0',cost_deductible_rate:'0',fiscal_competence_year:2026},{gross_amount:'14.50'},'gross_amount');
 assert.ok(!(await rows('vehicle_monthly')).some(r=>r.fiscal_year_id===year.id&&r.vehicle_id===vehicle.id&&r.month===12),'December must remain an empty test month');
 await roundtrip('vehicle_monthly',{fiscal_year_id:year.id,vehicle_id:vehicle.id,month:12,distance_km:'1234',notes:note},{distance_km:'1300'},'distance_km');
 await roundtrip('depreciable_assets',{fiscal_year_id:year.id,description:note,purchase_date:'2026-01-10',gross_amount:'1000',deductible_vat:'0',depreciation_rate:'0.2',first_fiscal_year:2026,is_planned:true},{gross_amount:'1100'},'gross_amount');
 await roundtrip('tax_credits',{description:note,original_amount:'100',credit_rate:'0.19',installment_count:1,first_fiscal_year:2026},{original_amount:'110'},'original_amount');
 await roundtrip('tax_deductions',{fiscal_year_id:year.id,description:note,amount:'100',payment_date:'2026-01-10'},{amount:'110'},'amount');
 console.log('PASS: all temporary staging rows removed; production untouched');
}finally{for(const client of clients)await client.auth.signOut({scope:'local'});}
