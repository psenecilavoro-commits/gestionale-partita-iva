import {test} from 'node:test';
import assert from 'node:assert/strict';
import {autoCell} from '../src/auto-cells.js';

const months=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
const records=months.map(Mese=>({Mese,Percorrenza:'—',Carburante:'—',Autostrada:'—','Rate auto':'—'})).concat([
  {Mese:'Totale registrato',Percorrenza:'—',Carburante:'—',Autostrada:'—','Rate auto':'—'},
  {Mese:'Stima annua',Percorrenza:'—',Carburante:'—',Autostrada:'—','Rate auto':'—'},
]);
const tables={
  fiscal_years:[{id:'fy',fiscal_year:2026,status:'open'}],
  vehicles:[{id:'car'}],
  vehicle_monthly:[{id:'km',fiscal_year_id:'fy',vehicle_id:'car',month:1,distance_km:'100.00'}],
  cost_categories:[
    {id:'toll',fiscal_year_id:'fy',code:'autostrada',vat_rate:'0.22',vat_deductible_rate:'1',cost_deductible_rate:'0.8',deductible_limit:null},
    {id:'lease',fiscal_year_id:'fy',code:'rate_auto',vat_rate:'0.22',vat_deductible_rate:'1',cost_deductible_rate:'0.8',deductible_limit:null},
  ],
  costs:[
    {id:'toll-1',fiscal_year_id:'fy',vehicle_id:'car',category_id:'toll',expense_date:'2026-01-01',gross_amount:'51.40'},
    {id:'lease-1',fiscal_year_id:'fy',vehicle_id:'car',category_id:'lease',expense_date:'2026-01-01',gross_amount:'663.16'},
  ],
};

test('Auto rende modificabili percorrenza, autostrada e rate ma non carburante',()=>{
  assert.equal(autoCell(records,'Percorrenza',0,tables,2026).record.id,'km');
  assert.equal(autoCell(records,'Autostrada',0,tables,2026).record.id,'toll-1');
  assert.equal(autoCell(records,'Rate auto',0,tables,2026).record.id,'lease-1');
  assert.equal(autoCell(records,'Carburante',0,tables,2026),null);
  assert.equal(autoCell(records,'Autostrada',12,tables,2026),null);
});

test('Auto permette una nuova cella mensile e blocca ambiguità o anno chiuso',()=>{
  const empty=autoCell(records,'Autostrada',1,tables,2026);
  assert.equal(empty.record,null);
  assert.equal(empty.editable,true);

  const duplicate={...tables,costs:[...tables.costs,{...tables.costs[0],id:'toll-2'}]};
  assert.equal(autoCell(records,'Autostrada',0,duplicate,2026).editable,false);

  const closed={...tables,fiscal_years:[{id:'fy',fiscal_year:2026,status:'closed'}]};
  assert.equal(autoCell(records,'Percorrenza',0,closed,2026).editable,false);
});
