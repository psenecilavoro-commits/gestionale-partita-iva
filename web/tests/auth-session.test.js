import test from 'node:test';
import assert from 'node:assert/strict';
import {watchSession} from '../src/auth-session.js';
const session=(id='s1',user='owner',token=1)=>({user:{id:user},access_token:`x.${Buffer.from(JSON.stringify({session_id:id,token})).toString('base64url')}.x`});
function fixture(onChange=()=>{}){
  let emit,finish,unsubscribed=false;
  const changes=[];
  const stop=watchSession({onAuthStateChange(fn){emit=fn;return {data:{subscription:{unsubscribe(){unsubscribed=true;}}}};},getUser(){return new Promise(resolve=>finish=resolve);}},s=>{changes.push(s);onChange(s);});
  return {emit:(...args)=>emit(...args),finish:r=>finish(r),changes,stop,get unsubscribed(){return unsubscribed;}};
}
test('tab return and token renewal preserve loaded screen, draft and disclosure',()=>{
  const state={data:[1],draft:'temporary unsaved text',page:'Costi',open:true};
  const f=fixture(()=>{state.data=null;state.draft='';state.page='Fatturato';state.open=false;});
  f.emit('INITIAL_SESSION',session());
  Object.assign(state,{data:[1],draft:'temporary unsaved text',page:'Costi',open:true});
  const original=f.changes.length;
  f.emit('SIGNED_IN',session());f.emit('TOKEN_REFRESHED',session('s1','owner',2));
  assert.equal(f.changes.length,original); // App reset callback never runs.
  assert.deepEqual(state,{data:[1],draft:'temporary unsaved text',page:'Costi',open:true});
  f.emit('SIGNED_OUT',null);
  assert.deepEqual(state,{data:null,draft:'',page:'Fatturato',open:false});
});
test('new login of same owner and different-session refresh invalidate',()=>{
  const f=fixture();f.emit('SIGNED_IN',session());f.emit('SIGNED_IN',session('s2'));f.emit('TOKEN_REFRESHED',session('s3'));
  assert.equal(f.changes.length,3);
});
test('logout/expired session clears and subsequent same-owner login reloads',()=>{
  const f=fixture();f.emit('SIGNED_IN',session());f.emit('SIGNED_OUT',null);f.emit('SIGNED_IN',session());
  assert.equal(f.changes.length,3);assert.equal(f.changes[1],null);
});
test('missing or malformed session id cannot silently preserve data',()=>{
  const f=fixture();f.emit('SIGNED_IN',session());f.emit('SIGNED_IN',{user:{id:'owner'},access_token:'invalid'});f.emit('TOKEN_REFRESHED',session(undefined,'other'));
  assert.equal(f.changes.length,3);
});
test('late startup response cannot overwrite logout or new access',async()=>{
  const f=fixture();f.emit('SIGNED_IN',session());f.emit('SIGNED_OUT',null);f.emit('SIGNED_IN',session('new'));
  f.finish({data:{user:null},error:{status:401}});await Promise.resolve();assert.equal(f.changes.length,3);
});
test('startup server rejection clears initial session; network error does not',async()=>{
  const f=fixture();f.emit('INITIAL_SESSION',session());f.finish({data:{user:null},error:{status:401}});await Promise.resolve();assert.equal(f.changes.at(-1),null);
  const g=fixture();g.emit('INITIAL_SESSION',session());g.finish({data:{user:null},error:{status:0}});await Promise.resolve();assert.equal(g.changes.length,1);
});
test('unsubscription ignores pending validation and later events',async()=>{
  const f=fixture();f.stop();f.finish({data:{user:null}});f.emit('SIGNED_IN',session());await Promise.resolve();assert.equal(f.changes.length,0);assert.equal(f.unsubscribed,true);
});
