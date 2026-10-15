import test from 'node:test';
import assert from 'node:assert/strict';
import {fiscalYearLayout} from '../src/fiscal-year-layout.js';
test('moves year controls before closure and replaces checkbox with enabled confirmation action in every year',()=>{
 for(const year of [2026,2027,2035])for(const action of ['chiusura','riapertura']){
  const result={tree:[{kind:'title',label:'Gestionale'},{kind:'subheader',label:'Anno fiscale'},{kind:'selectbox',key:'anno_fiscale_selezionato'},{kind:'success',label:'Stato anno'},{kind:'tabs',key:'schede_principali'}],sidebar:[{kind:'markdown',label:'### Gestione anno fiscale'},{kind:'checkbox',key:`${action}_anno_conferma_${year}`},{kind:'button',key:`${action}_anno_btn_${year}`,disabled:true}]};
  const before=JSON.stringify(result),layout=fiscalYearLayout(result);
  assert.equal(layout.tree.length,2);assert.equal(layout.sidebar[1].key,'anno_fiscale_selezionato');assert.equal(layout.sidebar.at(-1).disabled,false);assert.ok(!layout.sidebar.some(n=>n.kind==='checkbox'));assert.equal(layout.confirmations[action],`${action}_anno_conferma_${year}`);assert.equal(JSON.stringify(result),before);
 }
});
test('missing fiscal years move creation into sidebar without enabling closure or inventing confirmation',()=>{
 const layout=fiscalYearLayout({tree:[{kind:'subheader',label:'Anno fiscale'},{kind:'selectbox',key:'anno_fiscale_selezionato'},{kind:'button',label:'Crea anno fiscale 2035'}],sidebar:[]});
 assert.equal(layout.tree.length,0);assert.equal(layout.sidebar.at(-1).label,'Crea anno fiscale 2035');assert.deepEqual(layout.confirmations,{});
});
