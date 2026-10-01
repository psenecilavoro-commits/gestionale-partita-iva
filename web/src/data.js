import {createClient} from '@supabase/supabase-js';
export const PERSONAL_REF='mmkjtvebgtwsjatwifjv';
export function validateConfig(url,key,mode){
  if(!['staging','production'].includes(mode)) throw Error('Ambiente non configurato');
  if(!key?.startsWith('sb_publishable_')) throw Error('È richiesta una chiave publishable');
  const ref=new URL(url).hostname.split('.')[0];
  if(mode==='production'&&ref!==PERSONAL_REF) throw Error('Backend Personale non corrispondente');
  if(mode==='staging'&&ref===PERSONAL_REF) throw Error('Il collaudo non può usare il database di produzione');
  return ref;
}
export function configuredClient(){
  const mode=import.meta.env.VITE_APP_MODE || 'demo';
  if(mode==='demo')return null;
  const url=import.meta.env.VITE_SUPABASE_URL,key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  validateConfig(url,key,mode);
  return createClient(url,key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:false,storageKey:`piva-${mode}-auth`}});
}
export async function readTable(client,table){
  const rows=[],ids=new Set();let offset=0,total;
  while(true){
    const {data,error,count}=await client.from(table).select('*',{count:'exact'}).order('id').range(offset,offset+499);
    if(error)throw error;
    if(!data)throw Error('Lettura non confermata');
    if(total!==undefined&&count!==total)throw Error('Dati cambiati durante la lettura');
    total=count;
    for(const row of data){if(ids.has(row.id))throw Error('Righe duplicate durante la lettura');ids.add(row.id);rows.push(row);}
    offset+=data.length;
    if(!data.length||offset>=total)break;
  }
  return rows;
}
export async function applyMutations(client,mutations){
  const {data:identity,error:authError}=await client.auth.getUser();
  if(authError||!identity?.user)throw Error('Sessione scaduta: accedi nuovamente.');
  const insertedIds=new Map();
  const mapped=value=>Array.isArray(value)?value.map(mapped):value&&typeof value==='object'?Object.fromEntries(Object.entries(value).map(([k,v])=>[k,mapped(v)])):insertedIds.get(value)??value;
  for(const mutation of mutations){
    let query=client.from(mutation.table);
    query=mutation.operation==='insert'?query.insert(mapped(mutation.payload)):mutation.operation==='update'?query.update(mapped(mutation.payload)):query.delete();
    for(const [key,value] of mutation.filters)query=query.eq(key,mapped(value));
    const {data,error}=await query.select();
    if(error)throw error;
    const expected=mutation.expected_rows;
    if(!data||data.length!==expected)throw Error('Salvataggio non confermato o dati modificati altrove: aggiorna prima di riprovare.');
    if(mutation.operation==='insert')for(let i=0;i<data.length;i++)insertedIds.set(mutation.result_ids[i],data[i].id);
  }
}
