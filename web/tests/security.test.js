import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateConfig,PERSONAL_REF,readTable,applyMutations} from '../src/data.js';
test('staging rejects production backend and privileged keys',()=>{
  assert.throws(()=>validateConfig(`https://${PERSONAL_REF}.supabase.co`,'sb_publishable_test','staging'));
  assert.throws(()=>validateConfig('https://other.supabase.co','sb_secret_no','staging'));
  assert.throws(()=>validateConfig('https://other.supabase.co','sb_publishable_test','production'));
});

test('direct cell inserts need no temporary IDs, while engine IDs are resolved for dependent inserts',async()=>{
 const writes=[];
 const client={auth:{async getUser(){return {data:{user:{id:'owner'}}};}},from(table){return {insert(payload){writes.push({table,payload});return this;},async select(){return {data:[{id:'real-'+writes.length}]};}};}};
 await applyMutations(client,[{table:'monthly_reserves',operation:'insert',payload:{reserved_amount:'0.00'},filters:[],expected_rows:1},{table:'cost_categories',operation:'insert',payload:{name:'PC'},filters:[],expected_rows:1,result_ids:['temp']},{table:'annual_cost_estimates',operation:'insert',payload:{category_id:'temp'},filters:[],expected_rows:1}]);
 assert.equal(writes[2].payload.category_id,'real-2');
});
test('production permits only the original Personal project',()=>{
  assert.equal(validateConfig(`https://${PERSONAL_REF}.supabase.co`,'sb_publishable_test','production'),PERSONAL_REF);
});
test('pagination handles a server cap lower than the requested page',async()=>{
  const source=Array.from({length:11},(_,i)=>({id:String(i)}));
  const client={from(){return {select(){return this;},order(){return this;},async range(a,b){return {data:source.slice(a,Math.min(a+3,b+1)),count:source.length,error:null};}};}};
  assert.deepEqual(await readTable(client,'fixture'),source);
});