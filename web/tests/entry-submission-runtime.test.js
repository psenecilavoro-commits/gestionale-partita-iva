import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {loadPyodide} from 'pyodide';
import {confirmExplicitSubmission,FUEL_CONFIRMATION,VAT_CONFIRMATION} from '../src/entry-presentation.js';

test('fuel and VAT forms save through the explicit button without the redundant checkbox; unrelated checks and validation stay effective',async()=>{
 const py=await loadPyodide(),tables=JSON.parse(await readFile('public/demo.json','utf8'));
 py.FS.mkdir('/app');for(const [name,code] of Object.entries(JSON.parse(gunzipSync(await readFile('public/engine.json.gz')))))py.FS.writeFile('/app/'+name,code);
 py.runPython("import sys,json\nsys.path.insert(0,'/app')\nimport react_bridge");
 const user={id:'demo-owner',email:'demo@example.invalid'};
 const render=(inputs,event)=>{py.globals.set('request',JSON.stringify({tables,user,inputs,event}));return JSON.parse(py.runPython('react_bridge.render(json.loads(request))'));};
 const flat=nodes=>(nodes||[]).flatMap(n=>[n,...flat(n.children)]);
 let result=render({anno_fiscale_selezionato:2026,schede_principali:'Auto'});
 const type=Object.keys(result.inputs).find(k=>k.startsWith('auto_tipo_'));
 if(type)result=render({...result.inputs,[type]:'carburante'});
 const form=flat(result.tree).find(n=>n.kind==='form'&&n.children.some(c=>c.kind==='button'&&c.label==='Conferma operazione'));
 assert.ok(form);
 const nodes=flat([form]),button=nodes.find(n=>n.kind==='button'&&n.label==='Conferma operazione');
 const amount=nodes.find(n=>n.label==='Importo lordo (€)'),date=nodes.find(n=>n.label==='Data della spesa');
 const fuelConfirm=nodes.find(n=>n.label===FUEL_CONFIRMATION);
 const inputs={...result.inputs,[amount.key]:'5,00',[date.key]:'2026-01-01',[fuelConfirm.key]:false};
 result=render(confirmExplicitSubmission([form],button.key,inputs),button.key);
 assert.ok(result.mutations.some(m=>m.table==='costs'&&m.operation==='insert'&&m.payload.gross_amount==='5.00'));
 const bad=render(confirmExplicitSubmission([form],button.key,{...inputs,[amount.key]:'non valido'}),button.key);
 assert.equal(bad.mutations.length,0);
 py.runPython('react_bridge.clear_session()');
 result=render({anno_fiscale_selezionato:2027,schede_principali:'Accantonamenti'});
 const vatForm=flat(result.tree).find(n=>n.kind==='form'&&n.children.some(c=>c.kind==='button'&&c.label==='Conferma periodo IVA'));
 assert.ok(vatForm);
 const fields=flat([vatForm]),vatButton=fields.find(n=>n.kind==='button'&&n.label==='Conferma periodo IVA');
 const vatInputs={...result.inputs};
 for(const n of fields){
  if(['Primo mese','Ultimo mese'].includes(n.label))vatInputs[n.key]=1;
  if(n.kind==='text_input'&&n.label.includes('€; indicare 0 se assente'))vatInputs[n.key]='0';
  if(n.label===VAT_CONFIRMATION)vatInputs[n.key]=false;
  if(n.label?.startsWith('Ho riconciliato tutti'))vatInputs[n.key]=false;
 }
 const submitted=confirmExplicitSubmission([vatForm],vatButton.key,vatInputs);
 result=render(submitted,vatButton.key);
 const mutation=result.mutations.find(m=>m.table==='vat_periods'&&m.operation==='insert');
 assert.ok(mutation);assert.equal(mutation.payload.documents_complete,false);
 const invalid=render(confirmExplicitSubmission([vatForm],vatButton.key,{...vatInputs,[fields.find(n=>n.label==='Primo mese').key]:0}),vatButton.key);
 assert.equal(invalid.mutations.length,0);
});
