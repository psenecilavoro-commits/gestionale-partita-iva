import {test} from 'node:test';
import assert from 'node:assert/strict';
import {principalCreate,principalDelete,isPrincipalSummary} from '../src/principal-actions.js';
const tables={fiscal_years:[{id:'y26',fiscal_year:2026,status:'open'},{id:'y27',fiscal_year:2027,status:'open'},{id:'y30',fiscal_year:2030,status:'open'},{id:'closed',fiscal_year:2028,status:'closed'}],principals:[{id:'p',user_id:'owner',name:'Mandante esistente',active:true}],monthly_revenues:[],sales_vat_invoices:[]};
test('name-only creation normalizes whitespace and accents, defaults to active plurimandatario in every open year',()=>{
 for(const year of [2026,2027,2030]){
  const m=principalCreate(tables,'  Societa\u0300   Esempio  ',year);
  assert.deepEqual(m.payload,{name:'Società Esempio',enasarco_relationship:'plurimandatario',active:true});
  assert.equal(m.operation,'insert');assert.equal(m.expected_rows,1);
 }
 for(const value of ['', ' ', 'x'.repeat(121),'MESE','Totale mese','  MANDANTE  ESISTENTE '])assert.throws(()=>principalCreate(tables,value,2027));
 assert.throws(()=>principalCreate(tables,'Nuova',2028),/aperto/);assert.throws(()=>principalCreate(tables,'Nuova',2040),/aperto/);
});
test('deletion checks every year including zero revenue and documents, reports linked year and counts, preserves all original data',()=>{
 const withLinks=structuredClone(tables);
 withLinks.monthly_revenues=[{principal_id:'p',fiscal_year_id:'y26',month:1,amount:'0.00'},{principal_id:'p',fiscal_year_id:'y26',month:2,amount:'120.00'}];
 withLinks.sales_vat_invoices=[{principal_id:'p',fiscal_year_id:'y30',vat_amount:'0.00'}];
 const before=JSON.stringify(withLinks);
 assert.throws(()=>principalDelete(withLinks,'p',2027),error=>error.message.includes('2026: 2 registrazioni')&&error.message.includes('2030: 1 fatture'));
 assert.equal(JSON.stringify(withLinks),before);
});
test('deletion of an unused principal is precisely scoped and rejects stale, closed or ambiguous records',()=>{
 const m=principalDelete(tables,'p',2027);
 assert.deepEqual(m,{table:'principals',operation:'delete',filters:[['id','p'],['user_id','owner'],['name','Mandante esistente']],expected_rows:1});
 assert.throws(()=>principalDelete(tables,'missing',2027));assert.throws(()=>principalDelete(tables,'p',2028));
 assert.throws(()=>principalDelete({...tables,principals:[...tables.principals,...tables.principals]},'p',2027));
});
test('summary actions are attached only to the principal forecast table',()=>{
 assert.equal(isPrincipalSummary([{Mandante:'Esempio','Mesi compilati':0,Fatturato:'0,00 €','Media mesi compilati':'—','Stima annua':'—'}]),true);
 assert.equal(isPrincipalSummary([{Mandante:'Esempio','Rapporto Enasarco':'plurimandatario',Stato:'Attiva'}]),false);
 assert.equal(isPrincipalSummary([]),false);assert.equal(isPrincipalSummary(null),false);
});
