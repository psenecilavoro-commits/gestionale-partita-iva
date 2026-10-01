import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateConfig,PERSONAL_REF,readTable} from '../src/data.js';
test('staging rejects production backend and privileged keys',()=>{
  assert.throws(()=>validateConfig(`https://${PERSONAL_REF}.supabase.co`,'sb_publishable_test','staging'));
  assert.throws(()=>validateConfig('https://other.supabase.co','sb_secret_no','staging'));
  assert.throws(()=>validateConfig('https://other.supabase.co','sb_publishable_test','production'));
});
test('production permits only the original Personal project',()=>{
  assert.equal(validateConfig(`https://${PERSONAL_REF}.supabase.co`,'sb_publishable_test','production'),PERSONAL_REF);
});
test('pagination handles a server cap lower than the requested page',async()=>{
  const source=Array.from({length:11},(_,i)=>({id:String(i)}));
  const client={from(){return {select(){return this;},order(){return this;},async range(a,b){return {data:source.slice(a,Math.min(a+3,b+1)),count:source.length,error:null};}};}};
  assert.deepEqual(await readTable(client,'fixture'),source);
});
