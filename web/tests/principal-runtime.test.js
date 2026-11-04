import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {loadPyodide} from 'pyodide';
import {principalCreate,principalDelete} from '../src/principal-actions.js';

test('new principal appears in forecast and monthly table in both regimes; deleting unused principal removes only that principal',async()=>{
 const py=await loadPyodide();
 const source=JSON.parse(gunzipSync(await readFile('public/engine.json.gz')));
 py.FS.mkdir('/app');for(const [path,code] of Object.entries(source))py.FS.writeFile('/app/'+path,code);
 py.runPython("import sys,json\nsys.path.insert(0,'/app')\nimport react_bridge");
 const tables=JSON.parse(await readFile('public/demo.json','utf8'));
 const original=structuredClone(tables),mutation=principalCreate(tables,'Mandante temporanea',2027);
 tables.principals.push({id:'temporary',user_id:'demo-owner',...mutation.payload});
 const flatten=nodes=>(nodes||[]).flatMap(n=>[n,...flatten(n.children)]);
 function render(year){
  py.runPython('react_bridge.clear_session()');
  py.globals.set('request',JSON.stringify({tables,user:{id:'demo-owner',email:'demo@example.invalid'},inputs:{anno_fiscale_selezionato:year,schede_principali:'Fatturato'}}));
  return JSON.parse(py.runPython('react_bridge.render(json.loads(request))'));
 }
 for(const year of [2026,2027]){
  const result=render(year);assert.equal(result.mutations.length,0);
  const records=flatten(result.tree).filter(n=>n.kind==='table').map(n=>n.records);
  const summary=records.find(rows=>rows.some(r=>r.Mandante==='Mandante temporanea'&&Object.hasOwn(r,'Mesi compilati')));
  assert.ok(summary);assert.equal(summary.find(r=>r.Mandante==='Mandante temporanea').Fatturato,'0,00 €');
  const monthly=records.find(rows=>rows.length===12&&rows[0].Mese==='Gennaio');
  assert.equal(monthly[0]['Mandante temporanea'],'—');
 }
 principalDelete(tables,'temporary',2027);
 tables.principals=tables.principals.filter(p=>p.id!=='temporary');
 assert.deepEqual(tables,original);
 assert.ok(!JSON.stringify(render(2027).tree).includes('Mandante temporanea'));
});
