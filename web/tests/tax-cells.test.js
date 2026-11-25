import {test} from 'node:test';
import assert from 'node:assert/strict';
import defaults from '../src/tax-defaults.json' with {type:'json'};
import {taxCell,taxMutation,taxValue} from '../src/tax-cells.js';
test('annual parameters edit percentages and money, preserving other years and guarding conflicts/closed years',()=>{
 const tables={fiscal_years:[{id:'y',fiscal_year:2030,status:'open'}],fiscal_parameters:[]};
 const records=defaults[2].map(v=>({Parametro:v[1],Valore:v[2]}));
 const cell=taxCell(records,'Valore',1,tables,2030);
 assert.equal(cell.displayValue,3);assert.equal(cell.editable,true);
 assert.equal(taxValue('3,125','RATE'),'0.031250');
 assert.equal(taxValue('6.197,48','EUR'),'6197.480000');
 const insert=taxMutation(cell,tables,taxValue('2','RATE'));
 assert.equal(insert.payload.value,'0.020000');assert.equal(insert.payload.fiscal_year_id,'y');assert.equal(insert.payload.is_provisional,false);
 const record={...insert.payload,id:'p'};tables.fiscal_parameters=[record];
 const edit=taxCell(records,'Valore',1,tables,2030);
 assert.equal(taxMutation(edit,tables,'0.030000').operation,'update');
 tables.fiscal_parameters=[{...record,value:'0.05'}];assert.throws(()=>taxMutation(edit,tables,'0.04'),/altrove/);
 tables.fiscal_years[0].status='closed';assert.equal(taxCell(records,'Valore',1,tables,2030).editable,false);assert.throws(()=>taxMutation(edit,tables,'0.04'),/chiuso/);
 for(const bad of ['','-1','NaN','2.00000001'])assert.throws(()=>taxValue(bad,'RATE'));
 assert.throws(()=>taxValue('101','RATE'));assert.equal(taxCell(records,'Parametro',0,tables,2030),null);
});

test('prior-year contributions use annual saved parameters and survive a fresh editor',()=>{
 const tables={fiscal_years:[{id:'y',fiscal_year:2040,status:'open'}],fiscal_parameters:[]};
 const rows=[{Parametro:'Contributi anni precedenti effettivamente pagati nell’anno',Valore:'8.000,00 €'}];
 const cell=taxCell(rows,'Valore',0,tables,2040);
 const mutation=taxMutation(cell,tables,taxValue('12000','EUR'));
 assert.equal(mutation.payload.code,'contributi_ap_pagati');
 tables.fiscal_parameters=[{id:'saved',...mutation.payload}];
 assert.equal(taxCell(rows,'Valore',0,tables,2040).displayValue,'12000.000000');
 tables.fiscal_years[0].status='closed';
 assert.equal(taxCell(rows,'Valore',0,tables,2040).editable,false);
});
