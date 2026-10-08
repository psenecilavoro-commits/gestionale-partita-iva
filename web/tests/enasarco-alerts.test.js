import test from 'node:test';
import assert from 'node:assert/strict';
import {enasarcoAlerts,enasarcoSummary} from '../src/enasarco-alerts.js';
function fixture(){return {fiscal_years:[{id:'y26',fiscal_year:2026,status:'open'},{id:'y27',fiscal_year:2027,status:'closed'}],principals:[{id:'a',name:'A',enasarco_relationship:'plurimandatario'},{id:'b',name:'B',enasarco_relationship:'plurimandatario'}],fiscal_parameters:[{fiscal_year_id:'y26',code:'enasarco_massimale_pluri',value:'30478',is_provisional:false},{fiscal_year_id:'y27',code:'enasarco_massimale_pluri',value:'31000',is_provisional:true}],monthly_revenues:[]};}
test('only principal summary gets a final read-only STOP/VAI column, without mutating records',()=>{
  const records=['A','B','C'].map(Mandante=>({Mandante,'Mesi compilati':1,Fatturato:'100 €','Media mesi compilati':'100 €','Stima annua':'1200 €'}));
  const result=enasarcoSummary(records,[{name:'A',status:'stop'},{name:'B',status:'go'},{name:'C',status:'missing'}]);
  assert.deepEqual(result.map(r=>r.Enasarco),['STOP','VAI','—']);assert.deepEqual(Object.keys(result[0]).slice(-2),['Enasarco','Incidenza']);assert.equal(Object.hasOwn(records[0],'Enasarco'),false);
  const other=[{Mese:'Gennaio','Totale mese':'100 €'}];assert.equal(enasarcoSummary(other,[{name:'A',status:'stop'}]),other);
});
test('incidence uses annual estimates rather than recorded revenues and distinguishes missing from zero',()=>{
  const records=['250,00 €','750,00 €','0,00 €','—'].map((estimate,i)=>({Mandante:String(i),'Mesi compilati':1,Fatturato:'999,00 €','Media mesi compilati':'999,00 €','Stima annua':estimate}));
  const alerts=records.map(r=>({name:r.Mandante,status:'go'}));
  assert.deepEqual(enasarcoSummary(records,alerts).map(r=>r.Incidenza),['25,00 %','75,00 %','0,00 %','—']);
  assert.equal(enasarcoSummary([{...records[0],'Stima annua':'0,00 €'}],alerts)[0].Incidenza,'—');
});
test('STOP uses registered net annual revenues per principal, not projection or all principals combined',()=>{
  const t=fixture();t.monthly_revenues=[{fiscal_year_id:'y26',principal_id:'a',month:1,amount:'30478.01'},{fiscal_year_id:'y26',principal_id:'b',month:1,amount:'20000'}];
  const [a,b]=enasarcoAlerts(t,2026);assert.equal(a.status,'stop');assert.equal(a.total,3047801n);assert.equal(b.status,'go');assert.equal(b.remaining,1047800n);
});
test('exact cap, zero and missing month remain distinct',()=>{
  const t=fixture();t.monthly_revenues=[{fiscal_year_id:'y26',principal_id:'a',month:1,amount:'30478'},{fiscal_year_id:'y26',principal_id:'b',month:1,amount:'0'}];
  assert.deepEqual(enasarcoAlerts(t,2026).map(r=>r.status),['reached','go']);t.monthly_revenues.pop();assert.equal(enasarcoAlerts(t,2026)[1].status,'empty');
});
test('every year uses only its configured cap and preserves provisional and closed-year status',()=>{
  const t=fixture();t.monthly_revenues=[{fiscal_year_id:'y27',principal_id:'a',month:1,amount:'30500'},{fiscal_year_id:'y26',principal_id:'a',month:1,amount:'40000'}];
  const a=enasarcoAlerts(t,2027)[0];assert.equal(a.status,'go');assert.equal(a.remaining,50000n);assert.equal(a.provisional,true);assert.deepEqual(enasarcoAlerts(t,2028),[]);
});
test('missing/duplicate parameters, unknown relationships and ambiguous records never produce advice',()=>{
  const t=fixture();t.fiscal_parameters=[];assert.equal(enasarcoAlerts(t,2026)[0].status,'missing');
  const u=fixture();u.monthly_revenues=[{fiscal_year_id:'y26',principal_id:'a',month:1,amount:'100'},{fiscal_year_id:'y26',principal_id:'a',month:1,amount:'200'}];assert.equal(enasarcoAlerts(u,2026)[0].status,'invalid');
  u.principals[1].enasarco_relationship='unknown';assert.equal(enasarcoAlerts(u,2026)[1].status,'missing');
});
