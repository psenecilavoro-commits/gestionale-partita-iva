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
test('local document readers preserve original amounts and reject unsafe XML and PDF page limits',async()=>{
 const py=await loadPyodide();const source=JSON.parse(gunzipSync(await readFile('public/engine.json.gz')).toString());py.FS.mkdir('/app');
 for(const [path,text] of Object.entries(source))py.FS.writeFile('/app/'+path,text);
 for(const name of ['pypdf-6.19.0-py3-none-any.whl','defusedxml-0.7.1-py2.py3-none-any.whl']){py.FS.writeFile('/package.whl',await readFile('public/runtime/wheels/'+name));py.runPython("import zipfile\nwith zipfile.ZipFile('/package.whl') as wheel: wheel.extractall('/app')");}
 py.runPython("import sys,json\nsys.path.insert(0,'/app')\nimport react_bridge");
 const inspect=async(name,medical=false)=>{py.globals.set('document_request',JSON.stringify({base64:(await readFile('tests/fixtures/'+name)).toString('base64'),medical}));return JSON.parse(py.runPython('json.dumps(react_bridge.inspect_document(json.loads(document_request)))'));};
 const invoice=await inspect('invoice.pdf');assert.equal(invoice.needs_ocr,false);
 py.globals.set('document_text',invoice.text);assert.equal(py.runPython("from fatture_provvigioni import suggerisci_netto\nstr(suggerisci_netto(document_text)[0])"),'1234.56');
 const medical=await inspect('medical.pdf',true);py.globals.set('document_text',medical.text);assert.equal(py.runPython("from sanitarie_documenti import suggerisci_importo\nstr(suggerisci_importo(document_text))"),'123.45');
 await assert.rejects(inspect('too-many-pages.pdf'),/più di 4 pagine/);
 assert.equal(py.runPython("from fatture_provvigioni import _leggi_xml\nstr(_leggi_xml(b'<Fattura><DettaglioPagamento><ImportoPagamento>123.45</ImportoPagamento></DettaglioPagamento></Fattura>')[0])"),'123.45');
 assert.throws(()=>py.runPython("_leggi_xml(b'<!DOCTYPE x [<!ENTITY secret SYSTEM \\\"file:///secret\\\">]><x>&secret;</x>')"),/XML non leggibile o non sicuro/);
 assert.equal(py.runPython("str(suggerisci_netto('NETTO A PAGARE 12,50 13,50')[0])"),'None');
});
