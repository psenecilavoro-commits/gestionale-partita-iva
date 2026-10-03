import test from 'node:test';
import assert from 'node:assert/strict';
import {revenueCell,costCell} from '../src/revenue-cells.js';
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

test('ordinary annual cells work for every future year, including blanks, while derived values stay locked',()=>{
 for(const year of [2027,2028,2040]){
  const records=['Assicurazione','PC','Penale km','Carburante','Totale'].map(Voce=>({Voce,Registrato:'—','Totale annuo stimato':'—','Da dedurre':'—'}));
  const tables={fiscal_years:[{id:'y',fiscal_year:year,status:'open'}],cost_categories:[{id:'a',name:'Assicurazione',code:'assicurazione',fiscal_year_id:'y'}],annual_cost_estimates:[{id:'e',category_id:'a',fiscal_year_id:'y',estimated_gross_amount:'0.00'}]};
  assert.equal(costCell(records,'Totale annuo stimato',0,tables,year).record.estimated_gross_amount,'0.00');
  assert.equal(costCell(records,'Totale annuo stimato',1,tables,year).record,null);
  for(const i of [2,3,4])assert.equal(costCell(records,'Totale annuo stimato',i,tables,year),null);
  assert.equal(costCell(records,'Da dedurre',0,tables,year),null);
  tables.fiscal_years[0].status='closed';
  assert.equal(costCell(records,'Totale annuo stimato',0,tables,year).editable,false);
 }
});

test('cost estimates exclude derived columns, auto categories and closed years',()=>{
 const names=['Assicurazione','Auto · rate','Autostrada','Carburante','PC'];
 const records=names.map(Voce=>({Voce,Registrato:'—','Stima annua / valore file':'0,00 €'}));
 const tables={fiscal_years:[{id:'y',fiscal_year:2026,status:'open'}],cost_categories:names.map((name,i)=>({id:String(i),name,fiscal_year_id:'y'})),annual_cost_estimates:names.map((_,i)=>({id:'e'+i,category_id:String(i),fiscal_year_id:'y',estimated_gross_amount:'0.00'}))};
 assert.equal(costCell(records,'Registrato',0,tables,2026),null);
 for(const i of [1,2,3])assert.equal(costCell(records,'Stima annua / valore file',i,tables,2026),null);
 assert.equal(costCell(records,'Stima annua / valore file',4,tables,2026).record.estimated_gross_amount,'0.00');
 tables.fiscal_years[0].status='closed';
 assert.equal(costCell(records,'Stima annua / valore file',0,tables,2026).editable,false);
 assert.equal(costCell(records,'Stima annua / valore file',0,tables,2027),null);
});