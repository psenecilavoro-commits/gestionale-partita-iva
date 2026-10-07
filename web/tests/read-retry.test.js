import test from 'node:test';
import assert from 'node:assert/strict';
import {readWithJwtRetry} from '../src/read-retry.js';
import {readTable,applyMutations} from '../src/data.js';
const future={code:'PGRST303',message:'JWT issued at future'};
test('temporary future-issued JWT retries the same read and returns actual data',async()=>{
  const delays=[];let calls=0;
  const success={data:[{id:'actual-row'}],count:1,error:null};
  const result=await readWithJwtRetry(async()=>++calls<3?{error:future}:success,async ms=>delays.push(ms));
  assert.equal(result,success);assert.equal(calls,3);assert.deepEqual(delays,[1000,2000]);
});
test('persistent clock error stops after three retries and remains an error',async()=>{
  let calls=0;const delays=[];
  const result=await readWithJwtRetry(async()=>{calls++;return {error:future,data:null};},async ms=>delays.push(ms));
  assert.equal(calls,4);assert.deepEqual(delays,[1000,2000,4000]);assert.equal(result.error.code,'PGRST303');assert.match(result.error.message,/Aggiorna prospetto/);assert.equal(result.data,null);
});
test('expired JWT, permission errors, network failures and success are never retried',async()=>{
  for(const error of [{code:'PGRST303',message:'JWT expired'},{code:'42501',message:'permission denied'},{code:'',message:'Failed to fetch'},null]){
    let calls=0;const response={error,data:null};
    assert.equal(await readWithJwtRetry(async()=>{calls++;return response;},()=>assert.fail('unexpected retry')),response);assert.equal(calls,1);
  }
});
test('pagination still includes every row once after retry of a failed page',async()=>{
  const ranges=[];let calls=0;
  const client={from(){return {select(){return this;},order(){return this;},async range(start,end){ranges.push([start,end]);calls++;if(calls===2)return {error:future};return {data:start===0?[{id:'one'}]:[{id:'two'}],count:2,error:null};}};}};
  assert.deepEqual(await readTable(client,'example'),[{id:'one'},{id:'two'}]);assert.deepEqual(ranges,[[0,499],[1,500],[1,500]]);
});
test('writes are never replayed, including a future-issued JWT rejection',async()=>{
  let writes=0;
  const client={auth:{getUser:async()=>({data:{user:{id:'owner'}}})},from(){return {insert(){writes++;return this;},select:async()=>({error:future})};}};
  await assert.rejects(applyMutations(client,[{table:'example',operation:'insert',payload:{},filters:[],expected_rows:1}]),e=>e===future);assert.equal(writes,1);
});
