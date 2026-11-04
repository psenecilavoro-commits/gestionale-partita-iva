import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {loadPyodide} from 'pyodide';
test('annual forecast uses shared moved fields, no duplicate cash forms, parameters default without writes',async()=>{
 const py=await loadPyodide(),tables=JSON.parse(await readFile('public/demo.json','utf8'));
 py.FS.mkdir('/app');for(const [name,code] of Object.entries(JSON.parse(gunzipSync(await readFile('public/engine.json.gz')))))py.FS.writeFile('/app/'+name,code);
 py.runPython("import sys,json\nsys.path.insert(0,'/app')\nimport react_bridge");
 const render=inputs=>{py.globals.set('request',JSON.stringify({tables,user:{id:'demo-owner',email:'demo@example.invalid'},inputs}));return JSON.parse(py.runPython('react_bridge.render(json.loads(request))'));};
 const flat=nodes=>(nodes||[]).flatMap(n=>[n,...flat(n.children)]);
 let r=render({anno_fiscale_selezionato:2027,schede_principali:'Imposte'});
 const ap=flat(r.tree).find(n=>n.key?.startsWith('conto_contributi_ap_'));assert.ok(ap);
 assert.equal(r.mutations.length,0);assert.ok(!flat(r.tree).some(n=>n.label?.startsWith('Modifica un parametro')));
 r=render({...r.inputs,[ap.key]:4000});
 r=render({...r.inputs,schede_principali:'Detrazioni e deduzioni'});
 const fondo=flat(r.tree).find(n=>n.key?.startsWith('conto_fondo_pensione_'));assert.ok(fondo);
 r=render({...r.inputs,[fondo.key]:1000});
 r=render({...r.inputs,schede_principali:'Conto economico'});
 const nodes=flat(r.tree);assert.ok(!nodes.some(n=>n.key?.startsWith('cassa_')));
 assert.ok(!nodes.some(n=>n.kind==='number_input'&&/Fondo pensione|Contributi anni/.test(n.label)));
 const dump=JSON.stringify(r.tree);assert.ok(dump.includes('Costi deducibili annui stimati'));assert.ok(dump.includes('1.000,00'));
 r=render({...r.inputs,schede_principali:'Imposte'});assert.equal(r.inputs[ap.key],4000);
 r=render({...r.inputs,schede_principali:'Detrazioni e deduzioni'});assert.equal(r.inputs[fondo.key],1000);
 // Missing annual parameters render populated defaults, without generating DB mutations.
 tables.fiscal_parameters=tables.fiscal_parameters.filter(p=>p.fiscal_year_id!==tables.fiscal_years.find(y=>y.fiscal_year===2027).id);
 r=render({...r.inputs,schede_principali:'Imposte'});assert.equal(r.mutations.length,0);assert.ok(JSON.stringify(r.tree).includes('6.197,48'));
});
