import test from 'node:test';
import assert from 'node:assert/strict';
import {revenueCell} from '../src/revenue-cells.js';
test('monthly cells distinguish blank and zero, lock closed years and exclude totals',()=>{
 const months=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
 const records=months.map(Mese=>({Mese,A:'—','Totale mese':'—'}));
 const tables={fiscal_years:[{id:'y',fiscal_year:2026,status:'open'}],principals:[{id:'p',name:'A'}],monthly_revenues:[]};
 assert.equal(revenueCell(records,'A',0,tables,2026).record,null);
 assert.equal(revenueCell(records,'Totale mese',0,tables,2026),null);
 tables.monthly_revenues.push({id:'r',fiscal_year_id:'y',principal_id:'p',month:1,amount:'0.00'});
 assert.equal(revenueCell(records,'A',0,tables,2026).record.amount,'0.00');
 tables.fiscal_years[0].status='closed';
 assert.equal(revenueCell(records,'A',0,tables,2026).editable,false);
 assert.equal(revenueCell([{Mandante:'A',Fatturato:'100'}],'A',0,tables,2026),null);
});
