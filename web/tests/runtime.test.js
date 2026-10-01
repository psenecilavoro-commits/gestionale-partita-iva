import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {loadPyodide} from 'pyodide';
import {gunzipSync} from 'node:zlib';
test('browser Python runtime renders both regimes with original formulas',async()=>{
  const py=await loadPyodide();
  const source=JSON.parse(gunzipSync(await readFile('public/engine.json.gz')).toString());
  const tables=JSON.parse(await readFile('public/demo.json','utf8'));
  py.FS.mkdir('/app');
  for(const [p,s] of Object.entries(source))py.FS.writeFile(`/app/${p}`,s);
  py.runPython("import sys,json\nsys.path.insert(0,'/app')\nimport react_bridge");
  for(const year of [2026,2027])for(const page of ['Fatturato','Costi','Auto','Accantonamenti','Conto economico','Imposte','Detrazioni e deduzioni','Ammortamenti']){
    py.globals.set('request',JSON.stringify({tables,user:{id:'demo-owner',email:'demo@example.invalid'},inputs:{anno_fiscale_selezionato:year,schede_principali:page}}));
    const result=JSON.parse(py.runPython('react_bridge.render(json.loads(request))'));
    assert.ok(result.tree.length,`${year} ${page}`);
    assert.equal(result.mutations.length,0);
  }
  assert.equal(py.runPython("from decimal import Decimal as D\nfrom accantonamenti_confronto import ripartisci_residuo\nstr(ripartisci_residuo(D('11000'),D('4800'),8)['quota_mensile'])"),'1550');
});
