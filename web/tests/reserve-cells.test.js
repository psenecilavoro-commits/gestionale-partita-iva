import test from 'node:test';
import assert from 'node:assert/strict';
import {reserveCell,reserveMutation} from '../src/reserve-cells.js';
test('manual reserves and commissions distinguish zero, replace records, preserve notes and reject stale/closed cells',()=>{
 const months=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
 const records=months.map(Mese=>({Mese,'Accantonato · manuale':'—','Provvigioni nette · manuale':'—'}));
 const tables={fiscal_years:[{id:'y',fiscal_year:2026,status:'open'}],monthly_reserves:[],monthly_net_commissions:[]};
 const empty=reserveCell(records,'Accantonato · manuale',0,tables,2026);
 assert.equal(empty.record,null);assert.equal(reserveMutation(empty,tables,'0.00').operation,'insert');
 tables.monthly_reserves=[{id:'r',fiscal_year_id:'y',month:1,reserved_amount:'0.00',notes:'keep'}];
 const filled=reserveCell(records,'Accantonato · manuale',0,tables,2026);
 const mutation=reserveMutation(filled,tables,'100.00');assert.equal(mutation.operation,'update');assert.deepEqual(mutation.payload,{reserved_amount:'100.00'});
 tables.monthly_reserves=[{...tables.monthly_reserves[0],reserved_amount:'200.00'}];assert.throws(()=>reserveMutation(filled,tables,'100.00'));
 assert.equal(reserveCell(records,'Fatturato IVA esclusa',0,tables,2026),null);
 assert.equal(reserveCell(records,'Provvigioni nette · manuale',0,tables,2026).table,'monthly_net_commissions');
 tables.fiscal_years[0].status='closed';assert.equal(reserveCell(records,'Provvigioni nette · manuale',0,tables,2026).editable,false);assert.throws(()=>reserveMutation(empty,tables,'0.00'));
});


test('ordinary and future reserve sheets label and edit the VAT-inclusive bank receipt without changing the 2026 field',()=>{
 const months=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
 for(const year of [2027,2040]){
  const records=months.map(Mese=>({Mese,'Accantonato · manuale':'—','Provvigioni nette IVA inclusa':'—','Provvigioni nette - accantonato':'—'}));
  const tables={fiscal_years:[{id:'y',fiscal_year:year,status:'open'}],monthly_net_commissions:[],monthly_reserves:[]};
  const cell=reserveCell(records,'Provvigioni nette IVA inclusa',0,tables,year);
  assert.equal(cell.name,'Provvigioni nette IVA inclusa');assert.equal(reserveMutation(cell,tables,'10000.00').table,'monthly_net_commissions');
  assert.equal(reserveCell(records,'Provvigioni nette - accantonato',0,tables,year),null);
 }
});
