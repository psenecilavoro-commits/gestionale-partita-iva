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

