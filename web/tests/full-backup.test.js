import {test} from 'node:test';
import assert from 'node:assert/strict';
import JSZip from 'jszip';
import {completeBackup,digest,snapshot} from '../src/full-backup.js';
import {requireOnline} from '../src/offline-mode.js';

const tables={fiscal_years:[{fiscal_year:2026},{fiscal_year:2027},{fiscal_year:2030}],monthly_revenues:[{amount:'0.00',notes:null}],invoice_imports:[]};
async function fixture(){
 const source=new JSZip();source.file('sorgenti/migration/recovery-schema.sql','CREATE TABLE example();');
 const files={'index.html':'<html><head></head></html>','engine.json.gz':'engine','runtime/pyodide.mjs':'runtime','restore-source.zip':await source.generateAsync({type:'uint8array'})};
 for(const name of ['LEGGIMI.txt','Avvia-offline.cmd','avvia-offline.ps1','ripristina-dati.py'])files['backup-support/'+name]='support-'+name;
 const bytes=Object.fromEntries(Object.entries(files).map(([k,v])=>[k,typeof v==='string'?new TextEncoder().encode(v):v]));
 const manifest={format:1,revision:'revision',schemaDate:'2026-10-23',files:await Promise.all(Object.entries(bytes).map(async([path,value])=>({path,size:value.length,sha256:await digest(value)})))};
 return {bytes,manifest,fetchFile:async path=>path==='/backup-manifest.json'?Response.json(manifest):bytes[path.slice(1)]?new Response(bytes[path.slice(1)]):new Response('',{status:404})};
}
test('complete ZIP reopens with all years, original zero/null, offline application and recoverable sources; every final file hash verifies',async()=>{
 const f=await fixture(),progress=[];
 const zip=await JSZip.loadAsync(await completeBackup({tables,user:{id:'owner',email:'owner@example.invalid',access_token:'MUST NOT EXPORT'},revision:'revision',fetchFile:f.fetchFile,onProgress:m=>progress.push(m)}));
 const data=JSON.parse(await zip.file('offline/offline-data.json').async('string'));
 assert.deepEqual(data.tables,tables);assert.deepEqual(data.user,{id:'owner',email:'owner@example.invalid'});
 assert.equal(await zip.file('ripristino/dati-tutti-gli-anni.json').async('string'),await zip.file('offline/offline-data.json').async('string'));
 assert.match(await zip.file('offline/index.html').async('string'),/offline-config.js/);
 assert.match(await zip.file('offline/offline-config.js').async('string'),/__PIVA_OFFLINE__=true/);
 assert.ok(zip.file('ripristino/sorgenti/migration/recovery-schema.sql'));assert.ok(zip.file('Avvia-offline.cmd'));
 const manifest=JSON.parse(await zip.file('MANIFESTO.json').async('string'));
 assert.deepEqual(manifest.years,[2026,2027,2030]);assert.equal(manifest.counts.monthly_revenues,1);
 for(const [name,hash] of Object.entries(manifest.sha256))assert.equal(await digest(await zip.file(name).async('uint8array')),hash,name);
 assert.ok(progress.length>1);assert.equal(tables.monthly_revenues[0].notes,null);
});
test('missing, changed, incomplete and wrong-version deployments never produce a backup',async()=>{
 for(const corrupt of ['version','missing','changed','incomplete','path']){
  const f=await fixture();
  if(corrupt==='version')f.manifest.revision='new';
  if(corrupt==='missing')delete f.bytes['engine.json.gz'];
  if(corrupt==='changed')f.bytes['engine.json.gz']=new Uint8Array([1]);
  if(corrupt==='incomplete')f.manifest.files=[];
  if(corrupt==='path')f.manifest.files.push({path:'../escape'});
  await assert.rejects(completeBackup({tables,user:{id:'owner'},revision:'revision',fetchFile:f.fetchFile}));
 }
});
test('offline writes fail closed; snapshots are independent and exclude session secrets',()=>{
 assert.throws(()=>requireOnline(true),/sola consultazione/);assert.doesNotThrow(()=>requireOnline(false));
 assert.throws(()=>snapshot({},null,'r'));
 const copy=snapshot(tables,{id:'owner',refresh_token:'secret'},'r');copy.tables.fiscal_years[0].fiscal_year=1;
 assert.equal(tables.fiscal_years[0].fiscal_year,2026);assert.equal(copy.user.refresh_token,undefined);
});
