import React,{useState,useEffect,useRef} from 'react';
import {createRoot} from 'react-dom/client';
import {Calculator,Menu,ShieldCheck,TrendingUp,Receipt,Car,Wallet,ChartNoAxesCombined,Landmark,BadgePercent,Layers,X} from 'lucide-react';
import {configuredClient,readTable,applyMutations} from './data.js';
import './style.css';
import {prepareDocument} from './documents.js';

const NAV=['Fatturato','Costi','Auto','Accantonamenti','Conto economico','Imposte','Detrazioni e deduzioni','Ammortamenti'];
const NAV_ICONS=[TrendingUp,Receipt,Car,Wallet,ChartNoAxesCombined,Landmark,BadgePercent,Layers];
function Markdown({text=''}){
 const inline=line=>line.split(/(\*\*.*?\*\*)/g).map((part,i)=>part.startsWith('**')?<strong key={i}>{part.slice(2,-2)}</strong>:part);
 return <div className="prose">{String(text).split('\n').map((line,i)=>{const heading=line.match(/^(#{1,4})\s+(.+)$/);if(heading){const Tag=heading[1].length<3?'h2':'h3';return <Tag key={i}>{inline(heading[2])}</Tag>;}return line.trim()?<p key={i}>{inline(line)}</p>:null;})}</div>;
}
const client=configuredClient();
const isStaging=import.meta.env.VITE_APP_MODE==='staging';
function encodeFile(bytes){let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(binary);}
function Download({node}){
  const [href,setHref]=useState('');
  useEffect(()=>{
    const bytes=Uint8Array.from(atob(node.data.base64),c=>c.charCodeAt(0));
    const url=URL.createObjectURL(new Blob([bytes],{type:node.mime}));
    setHref(url);
    return()=>URL.revokeObjectURL(url);
  },[node.data.base64,node.mime]);
  return <a className="download-link" href={href||undefined} download={node.file_name} aria-disabled={!href}>{node.label}</a>;
}
function Table({records}){
  if(!Array.isArray(records))return <p>Nessuna riga disponibile.</p>;
  const cols=[...new Set(records.flatMap(r=>Object.keys(r)))];
  return <div className="table-scroll"><table><thead><tr>{cols.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{records.map((r,i)=><tr key={i}>{cols.map(c=><td key={c}>{r[c]===null?'—':String(r[c]??'')}</td>)}</tr>)}</tbody></table></div>;
}
function Nodes({nodes=[],values,onChange,onClick,onUpload,busy}){
  return nodes.map(n=>{
    const children=<Nodes nodes={n.children} values={values} onChange={onChange} onClick={onClick} onUpload={onUpload} busy={busy}/>;
    const value=values[n.key]??n.value;
    const change=v=>onChange(n.key,v);
    let el;
    switch(n.kind){
      case 'title':el=n.label==='Gestionale Partita IVA'?null:<h1>{n.label}</h1>;break;
      case 'subheader':el=<h2>{n.label}</h2>;break;
      case 'caption':el=<p className="caption">{n.label}</p>;break;
      case 'markdown':el=<Markdown text={n.label}/>;break;
      case 'write':case 'code':el=<p style={{whiteSpace:'pre-wrap'}}>{n.label}</p>;break;
      case 'info':case 'warning':case 'error':case 'success':el=<p role={n.kind==='error'?'alert':undefined} className={`notice ${n.kind}`}>{n.label}</p>;break;
      case 'table':el=<Table records={n.records}/>;break;
      case 'metric':el=<div className="metric"><small>{n.label}</small><strong>{String(n.value)}</strong></div>;break;
      case 'divider':el=<hr/>;break;
      case 'button':el=<button disabled={busy||n.disabled} onClick={()=>onClick(n.key)}>{n.label}</button>;break;
      case 'text_input':case 'number_input':case 'date_input':el=<label>{n.label}<input disabled={busy||n.disabled} type={n.kind==='date_input'?'date':n.kind==='number_input'?'number':n.type==='password'?'password':'text'} value={value??''} min={n.min_value} max={n.max_value} step={n.step} placeholder={n.placeholder} onChange={e=>change(n.kind==='number_input'?Number(e.target.value):e.target.value)}/></label>;break;
      case 'checkbox':el=<label className="check"><input type="checkbox" disabled={busy||n.disabled} checked={Boolean(value)} onChange={e=>change(e.target.checked)}/>{n.label}</label>;break;
      case 'radio':case 'selectbox':el=<label>{n.label}<select disabled={busy||n.disabled} value={n.options.findIndex(o=>o===value)} onChange={e=>change(n.options[Number(e.target.value)])}>{n.options.map((o,i)=><option key={i} value={i}>{n.option_labels[i]}</option>)}</select></label>;break;
      case 'file_uploader':el=<label>{n.label}<input type="file" multiple={n.accept_multiple_files} disabled={busy} onChange={e=>onUpload(n.key,[...e.target.files],n.accept_multiple_files)}/></label>;break;
      case 'tabs':el=n.key==='schede_principali'?null:<div className="columns">{n.options.map(o=><button key={o} disabled={busy} onClick={()=>onChange(n.key,o)}>{o}</button>)}</div>;break;
      case 'tab':el=n.hidden?null:<section className="card">{children}</section>;break;
      case 'form':el=<div className="form">{children}</div>;break;
      case 'expander':case 'popover':el=<details><summary>{n.label}</summary>{children}</details>;break;
      case 'columns':el=<div className="columns">{children}</div>;break;
      case 'column':case 'container':case 'placeholder':case 'spinner':el=<div>{children}</div>;break;
      case 'link':el=<a href={n.url} target="_blank" rel="noreferrer">{n.label}</a>;break;
      case 'download':el=<Download node={n}/>;break;
      default:el=<p role="alert">Elemento da completare: {n.kind}</p>;
    }
    return <React.Fragment key={n.id}>{el}</React.Fragment>;
  });
}
function App(){
  const [user,setUser]=useState(client?null:{id:'demo-owner',email:'Collaudo · dati sintetici'});
  const [result,setResult]=useState(null),[values,setValues]=useState({}),[busy,setBusy]=useState(false),[error,setError]=useState(''),[mobile,setMobile]=useState(false);
  const worker=useRef(),tables=useRef(),pending=useRef(new Map()),seq=useRef(0),epoch=useRef(0);
  const currentValues=useRef({});
  useEffect(()=>{
    worker.current=new Worker(new URL('./engine.worker.js',import.meta.url),{type:'module'});
    worker.current.onmessage=({data})=>{const p=pending.current.get(data.id);pending.current.delete(data.id);if(data.error)p?.reject(Error(data.error));else p?.resolve(data.result);};
    return()=>worker.current.terminate();
  },[]);
  useEffect(()=>{
    if(!client)return;
    client.auth.getUser().then(({data})=>setUser(data.user));
    const {data}=client.auth.onAuthStateChange((event,session)=>{if(event==='TOKEN_REFRESHED')return;if(!session)worker.current?.postMessage({id:++seq.current,request:{operation:'clear_session'}});epoch.current++;tables.current=null;currentValues.current={};setBusy(false);setValues({});setResult(null);setUser(session?.user??null);});
    return()=>data.subscription.unsubscribe();
  },[]);
  async function load(){
    if(!client){tables.current=await (await fetch('/demo.json')).json();return;}
    const schema=await (await fetch('/schema.json')).json();
    const names=[...schema.tables.map(t=>t.name),...['sales_vat_invoices','vat_periods','pension_payments','purchase_cost_links']];
    const pairs=await Promise.all(names.map(async name=>[name,await readTable(client,name)]));
    tables.current=Object.fromEntries(pairs);
  }
  async function run(event,inputs=currentValues.current){
    const ticket=epoch.current;setBusy(true);setError('');
    try{
      if(!tables.current)await load();
      const evaluate=()=>new Promise((resolve,reject)=>{const id=++seq.current;pending.current.set(id,{resolve,reject});worker.current.postMessage({id,request:{tables:tables.current,user,event,inputs}});});
      let next=await evaluate();
      if(ticket!==epoch.current)return;
      if(next.mutations.length){
        if(client){await applyMutations(client,next.mutations);await load();}
        else tables.current=next.tables;
        inputs=next.inputs;event=null;next=await evaluate();
      }
      if(ticket===epoch.current){setResult(next);currentValues.current=next.inputs;setValues(next.inputs);}
    }catch(e){if(ticket===epoch.current)setError(e.message);}
    finally{if(ticket===epoch.current)setBusy(false);}
  }
  useEffect(()=>{if(user)run(null);},[user]);
  function change(key,value){
    if(key==='anno_fiscale_selezionato'){currentValues.current={};setResult(null);}
    currentValues.current={...currentValues.current,[key]:value};setValues(currentValues.current);
    if(key==='anno_fiscale_selezionato'||key==='schede_principali'||typeof value==='boolean'||Array.isArray(value)||typeof value==='number')run(null);
    else if(['selectbox','radio','tabs','file_uploader'].includes(findKind(result?.tree,key)))run(null);
  }
  async function upload(key,files,multiple){
    const ticket=epoch.current;setBusy(true);setError('');
    try{
      const maximum=key.startsWith('fatture_upload_')?40:80;
      if(files.length>10||files.some(f=>!f.size||f.size>8*1024*1024)||files.reduce((n,f)=>n+f.size,0)>maximum*1024*1024)throw Error('Massimo 10 documenti, 8 MB ciascuno; controlla la dimensione del lotto.');
      const inspect=request=>new Promise((resolve,reject)=>{const id=++seq.current;pending.current.set(id,{resolve,reject});worker.current.postMessage({id,request});});
      const prepared=[];
      for(const file of files){
        const base64=encodeFile(new Uint8Array(await file.arrayBuffer()));
        let document;try{document=await prepareDocument(file,base64,inspect,key.startsWith('san_documenti_'));}catch(error){document={document_error:error.message};}
        prepared.push({name:file.name,base64,...document});
      }
      if(ticket!==epoch.current)return;
      currentValues.current={...currentValues.current,[key]:multiple?prepared:prepared[0]};setValues(currentValues.current);await run(null);
    }catch(error){if(ticket===epoch.current)setError(error.message);}
    finally{if(ticket===epoch.current)setBusy(false);}
  }
  function findKind(nodes,key){for(const n of nodes||[]){if(n.key===key)return n.kind;const found=findKind(n.children,key);if(found)return found;}return null;}
  async function login(e){e.preventDefault();setBusy(true);setError('');const f=new FormData(e.target);const {error}=await client.auth.signInWithPassword({email:String(f.get('email')).trim(),password:String(f.get('password'))});e.target.reset();setBusy(false);if(error)setError('Accesso non riuscito. Controlla le credenziali.');}
  const page=values.schede_principali||'Fatturato';
  return <div className="shell">{mobile&&<button className="backdrop" aria-label="Chiudi menu laterale" onClick={()=>setMobile(false)}/>}<aside aria-label="Menu principale" className={mobile?'sidebar shown':'sidebar'}><div className="brand"><div className="brand-icon"><Calculator/></div><div><strong>Gestionale</strong><small>Partita IVA · Personale</small></div><button className="side-close" aria-label="Chiudi menu" onClick={()=>setMobile(false)}><X size={18}/></button></div><div className="nav-label">IL TUO GESTIONALE</div><nav aria-label="Sezioni">{NAV.map((p,i)=><button key={p} className={page===p?'active':''} aria-current={page===p?'page':undefined} disabled={busy||!user} onClick={()=>{change('schede_principali',p);setMobile(false);}}>{React.createElement(NAV_ICONS[i],{size:18,"aria-hidden":true})}<span>{p}</span></button>)}</nav><Nodes nodes={result?.sidebar.filter(n=>!['Utente autenticato',user?.email,'Esci'].includes(n.label))} values={values} onChange={change} onClick={event=>run(event)} onUpload={upload} busy={busy}/><footer><ShieldCheck size={16}/> {client?'Accesso protetto':'Collaudo isolato'}<small>{user?.email}</small></footer></aside><main><header className="page-header"><div><p className="eyebrow">PARTITA IVA · PERSONALE</p><h1>{user?page:"Benvenuto"}</h1><p className="page-description">{user?"Un quadro chiaro della tua attività, mese dopo mese.":"Accedi al tuo spazio per tenere tutto sotto controllo."}</p></div><span className="environment-tag"><ShieldCheck size={15}/>{isStaging||!client?"Collaudo gratuito":"Accesso protetto"}</span></header><button className="menu" onClick={()=>setMobile(!mobile)} aria-label="Apri menu"><Menu/></button><div className="banner">{isStaging?'AMBIENTE DI COLLAUDO · dati sintetici · database separato':client?'Gestionale Partita IVA':'AMBIENTE DI COLLAUDO · dati sintetici · nessun collegamento al database reale'}</div>{client&&user&&<button onClick={async()=>{await client.auth.signOut({scope:'local'});}}>Esci</button>}{error&&<p role="alert" className="notice error">{error}</p>}{!user?<form onSubmit={login} className="login"><h1>Accedi</h1><label>Email<input name="email" type="email" required autoComplete="username"/></label><label>Password<input name="password" type="password" required autoComplete="current-password"/></label><button disabled={busy}>Accedi</button></form>:<>{busy&&<p role="status">{result?'Aggiornamento…':'Preparazione del gestionale e del motore di calcolo…'}</p>}<Nodes nodes={result?.tree} values={values} onChange={change} onClick={event=>run(event)} onUpload={upload} busy={busy}/><button disabled={busy} onClick={()=>run(null)}>Aggiorna prospetto</button></>}</main></div>;
}
createRoot(document.getElementById('root')).render(<App/>);
