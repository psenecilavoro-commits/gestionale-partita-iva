// Run explicitly; test credentials are local and never committed.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createClient} from '@supabase/supabase-js';
import {readTable,applyMutations} from '../src/data.js';
const users=JSON.parse(fs.readFileSync('.staging-test-users.json'));
const url='https://gbtvscldenpmvcvwognw.supabase.co';
const key='sb_publishable_5lyEqt6VE7BLi8JNA7-dcw_1ZQz0EcV';
const clients=users.map(()=>createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}}));
for(let i=0;i<2;i++){
 const {error}=await clients[i].auth.signInWithPassword(users[i]);
 assert.equal(error,null,error?.message);
 const {data}=await clients[i].auth.getUser();assert.equal(data.user.id,users[i].id);
}
const first=clients[0],second=clients[1];
const {data:years,error}=await first.from('fiscal_years').select('*');assert.equal(error,null);
let year=years.find(y=>y.fiscal_year===2026);
if(!year){const r=await first.from('fiscal_years').insert({fiscal_year:2026}).select().single();assert.equal(r.error,null,r.error?.message);year=r.data;}
assert.equal((await readTable(second,'fiscal_years')).length,0);
const blocked=await second.from('fiscal_years').insert({user_id:users[0].id,fiscal_year:2027});assert.ok(blocked.error);
await applyMutations(first,[{table:'fiscal_years',operation:'update',payload:{status:'closed'},filters:[['id',year.id]],expected_rows:1}]);
assert.equal((await readTable(first,'fiscal_years'))[0].status,'closed');
await applyMutations(first,[{table:'fiscal_years',operation:'update',payload:{status:'open'},filters:[['id',year.id]],expected_rows:1}]);
const anon=createClient(url,key,{auth:{persistSession:false}});
const publicRead=await anon.from('fiscal_years').select('*');assert.ok(publicRead.error||publicRead.data.length===0);
for(const client of clients)assert.equal((await client.auth.signOut()).error,null);
console.log('PASS: real Auth password/JWT, owner isolation, blocked cross-owner insert, close/reopen via transport, anonymous protection, logout');
