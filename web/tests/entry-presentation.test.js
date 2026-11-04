import {test} from 'node:test';
import assert from 'node:assert/strict';
import {isCostReadonly,isCostSummary,confirmExplicitSubmission,FUEL_CONFIRMATION,VAT_CONFIRMATION,withoutLegacyPurchaseXML} from '../src/entry-presentation.js';

test('grey Cost values use actual edit eligibility in every regime, including closed and offline years',()=>{
 for(const year of [2026,2027,2040]){
  const column=year===2026?'Stima annua / valore file':'Totale annuo stimato';
  const rows=['Assicurazione','Carburante','Autostrada','Auto · rate','Penale km'].map(Voce=>({Voce,Registrato:'—',[column]:'—','Da dedurre':'—'}));
  const data={fiscal_years:[{id:'y',fiscal_year:year,status:'open'}],cost_categories:[{id:'c',fiscal_year_id:'y',name:'Assicurazione',code:'assicurazione'}],annual_cost_estimates:[{id:'e',fiscal_year_id:'y',category_id:'c'}]};
  assert.equal(isCostSummary(rows),true);assert.equal(isCostReadonly(rows,'Voce',0,data,year),false);
  assert.equal(isCostReadonly(rows,column,0,data,year),false);
  for(const c of ['Registrato','Da dedurre'])assert.equal(isCostReadonly(rows,c,0,data,year),true);
  for(let i=1;i<rows.length;i++)assert.equal(isCostReadonly(rows,column,i,data,year),true);
  assert.equal(isCostReadonly(rows,column,0,data,year,true),true);
  data.fiscal_years[0].status='closed';assert.equal(isCostReadonly(rows,column,0,data,year),true);
 }
 assert.equal(isCostReadonly([{Mese:'Gennaio'}],'Mese',0,{},2027),false);
});
test('explicit submission confirms only its own redundant checkbox; reconciliation, VAT inclusion and deletion stay unchanged',()=>{
 for(const [label,submit] of [[FUEL_CONFIRMATION,'Conferma operazione'],[VAT_CONFIRMATION,'Conferma periodo IVA']]){
  const tree=[{kind:'container',children:[{kind:'form',children:[{kind:'checkbox',key:'confirm',label},{kind:'checkbox',key:'reconciled',label:'Ho riconciliato tutti i documenti'},{kind:'button',key:'save',label:submit}]}]}];
  const inputs={confirm:false,reconciled:false,delete:false,vat:true};
  assert.equal(confirmExplicitSubmission(tree,null,inputs),inputs);assert.equal(confirmExplicitSubmission(tree,'other',inputs),inputs);
  assert.deepEqual(confirmExplicitSubmission(tree,'save',inputs),{...inputs,confirm:true});assert.equal(inputs.confirm,false);
  assert.equal(confirmExplicitSubmission([{kind:'form',children:[{kind:'checkbox',key:'confirm',label:'Altro controllo'},{kind:'button',key:'save',label:submit}]}],'save',inputs),inputs);
 }
});
test('legacy XML importer is removed without hiding adjacent manual invoice and monthly review sections',()=>{
 const before={kind:'form',label:'Registra o modifica una fattura'},after={kind:'subheader',label:'Quadro mensile e controllo dei dati'},divider={kind:'divider'};
 const nodes=[before,divider,{kind:'subheader',label:"Importa una fattura d'acquisto XML"},{kind:'caption'},{kind:'file_uploader'},divider,after];
 assert.deepEqual(withoutLegacyPurchaseXML(nodes),[before,divider,after]);
 const other=[before,after];assert.equal(withoutLegacyPurchaseXML(other),other);
});
