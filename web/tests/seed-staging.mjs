import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
import {createClient} from '@supabase/supabase-js';
const [user]=JSON.parse(fs.readFileSync('.staging-test-users.json'));
const client=createClient('https://gbtvscldenpmvcvwognw.supabase.co','sb_publishable_5lyEqt6VE7BLi8JNA7-dcw_1ZQz0EcV',{auth:{persistSession:false,autoRefreshToken:false}});
const login=await client.auth.signInWithPassword(user);if(login.error)throw login.error;
const fixture=JSON.parse(fs.readFileSync('public/demo.json'));
const columns=JSON.parse(fs.readFileSync('../migration/staging-columns.json'));
const mapping=new Map([['demo-owner',user.id]]);
for(const rows of Object.values(fixture))for(const row of rows)mapping.set(row.id,randomUUID());
const existing=await client.from('fiscal_years').select('*');if(existing.error)throw existing.error;
for(const year of existing.data)mapping.set('demo-year-'+year.fiscal_year,year.id);
const order=['fiscal_years','principals','vehicles','fiscal_parameters','annual_settings','cost_categories','annual_cost_estimates','estimate_monthly_allocations','monthly_revenues','monthly_reserves','monthly_net_commissions','vehicle_year_settings','vehicle_monthly','costs','contributions','tax_deductions','tax_credits','purchase_vat_invoices','vat_adjustments','depreciable_assets'];
for(const table of order){
 const allowed=columns.filter(c=>c.table===table).map(c=>c.name);
 let records=fixture[table].map(row=>Object.fromEntries(Object.entries(row).filter(([k])=>allowed.includes(k)).map(([k,v])=>[k,mapping.get(v)??v])));
 if(table==='fiscal_years')records=records.filter(r=>!existing.data.some(y=>y.fiscal_year===r.fiscal_year));
 if(table==='fiscal_parameters')records=records.map(r=>({...r,unit:'EUR'}));
 if(records.length){const r=await client.from(table).insert(records);if(r.error)throw Error(table+': '+r.error.message);console.log(table+': '+records.length);}
}
await client.auth.signOut();
