import React,{useState,useEffect,useRef,createContext,useContext} from 'react';
import {createRoot} from 'react-dom/client';
import {Calculator,Menu,ShieldCheck,TrendingUp,Receipt,Car,Wallet,ChartNoAxesCombined,Landmark,BadgePercent,Layers,Upload,X} from 'lucide-react';
import {configuredClient,readTable,applyMutations} from './data.js';
import './style.css';
import {prepareDocument} from './documents.js';
import {revenueCell,costCell} from './revenue-cells.js';
import {reserveCell,reserveMutation,RESERVE_LABELS} from './reserve-cells.js';
import {autoCell} from './auto-cells.js';
import {splitGross,grossForRecord} from './revenue-vat.js';
import {watchSession} from './auth-session.js';
import InvoiceImport from './InvoiceImport.jsx';
import {enasarcoAlerts,enasarcoSummary} from './enasarco-alerts.js';
const EnasarcoContext=createContext([]);

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
function tableValue(value,column,fallback=''){
  const text=String(value??fallback);
  return column==='Percorrenza'?text.replace(/,(\d*?)0+(\s*km)$/,(match,decimals,unit)=>(decimals?','+decimals:'')+unit):text;
}
function Table({records,editTable}){
  const alerts=useContext(EnasarcoContext);
  records=enasarcoSummary(records,alerts);
  if(!Array.isArray(records))return <p>Nessuna riga disponibile.</p>;
  if(!editTable&&records.every(r=>Object.hasOwn(r,'VOCE')&&Object.hasOwn(r,'VALORE')))records=records.map(r=>r.VOCE==='Fatturato'?{...r,VOCE:'Fatturato stimato'}:r);
  const cols=[...new Set(records.flatMap(r=>Object.keys(r)))];
  const reserveSheet=cols.includes('Accantonato · manuale')&&cols.includes('Provvigioni nette · manuale');
  const monthlySheet=reserveSheet||(cols.includes('Totale mese')&&cols.includes('Mese'))||cols.includes('Stima annua / valore file')||cols.includes('Totale annuo stimato')||(['Mese','Percorrenza','Carburante','Autostrada','Rate auto'].every(col=>cols.includes(col)));
  return <div className={`table-scroll${editTable&&monthlySheet?' revenue-sheet':''}${cols.includes('Percorrenza')&&cols.includes('Rate auto')?' auto-sheet':''}`}><table><thead><tr>{cols.map(c=><th key={c}>{c==='Stima annua / valore file'?'Stima annua / valore finale':(reserveSheet?RESERVE_LABELS[c]||c:c)}</th>)}</tr></thead><tbody>{records.map((r,i)=><tr key={i}>{cols.map(c=><td key={c}>{editTable?.(records,c,i)?<button className="cell-edit" disabled={!editTable(records,c,i).editable} aria-label={`Modifica ${r.Voce||c}, ${r.Mese||"stima annua"}`} onClick={()=>editTable(records,c,i,true)}>{tableValue(r[c],c,'—')}</button>:r[c]===null?'—':c==='IVA compresa'&&typeof r[c]==='boolean'?(r[c]?'Sì':'No'):tableValue(r[c],c)}</td>)}</tr>)}</tbody></table></div>;
}
function Nodes({nodes=[],values,onChange,onClick,onUpload,busy,editTable}){
  const disclosure=nodes.some(n=>n.kind==='selectbox'&&n.label==='Versamento pensione da registrare o modificare')?{label:'Versamento pensione da registrare o modificare',submit:'Conferma versamento pensione'}:{label:'Registra o modifica una fattura',submit:'Salva fattura verificata'};
  const invoiceStart=nodes.findIndex(n=>n.kind==='selectbox'&&n.label===disclosure.label);
  const invoiceEnd=nodes.findIndex((n,i)=>i>invoiceStart&&n.kind==='form'&&n.children?.some(c=>c.kind==='button'&&c.label===disclosure.submit));
  if(invoiceStart>=0&&invoiceEnd>invoiceStart){
    const props={values,onChange,onClick,onUpload,busy,editTable};
    return <><Nodes nodes={nodes.slice(0,invoiceStart)} {...props}/><details><summary>{disclosure.label}</summary><Nodes nodes={nodes.slice(invoiceStart,invoiceStart+1)} {...props}/><Nodes nodes={nodes.slice(invoiceStart+1,invoiceEnd+1)} {...props}/></details><Nodes nodes={nodes.slice(invoiceEnd+1)} {...props}/></>;
  }
  if((values.schede_principali||'Fatturato')==='Fatturato'&&Number(values.anno_fiscale_selezionato)!==2026){
    const start=nodes.findIndex(n=>n.label==='IVA vendite documentata');
    if(start>=0){
      const end=nodes.findIndex((n,i)=>i>start&&n.kind==='subheader');
      const props={values,onChange,onClick,onUpload,busy,editTable};
      return <><Nodes nodes={nodes.slice(0,start)} {...props}/><details><summary>IVA vendite documentata</summary><Nodes nodes={nodes.slice(start+1,end>=0?end:undefined)} {...props}/></details>{end>=0&&<Nodes nodes={nodes.slice(end)} {...props}/>}</>;
    }
  }
  if(values.schede_principali==='Costi'&&Number(values.anno_fiscale_selezionato)!==2026){
    const start=nodes.findIndex(n=>n.label==='**Aggiungi una spesa o una stima**');
    if(start>=0){
      const end=nodes.findIndex((n,i)=>i>start&&n.kind==='subheader');
      nodes=[...nodes.slice(0,start),...(end>=0?nodes.slice(end):[])];
    }
  }
  if(values.schede_principali==='Accantonamenti'){
    const uploadStart=nodes.findIndex(n=>n.label==='#### Carica fatture → provvigioni nette');
    if(uploadStart>=0){
      const uploadEnd=nodes.findIndex((n,i)=>i>uploadStart&&(n.kind==='subheader'||n.kind==='markdown'&&n.label?.startsWith('#### ')));
      nodes=nodes.filter((n,i)=>i<uploadStart||(uploadEnd>=0&&i>=uploadEnd));
    }
  }
  if(values.schede_principali==='Auto'){
    const start=nodes.findIndex(n=>n.kind==='subheader'&&n.label==='Registra o modifica le spese');
    const end=start>=0?nodes.findIndex((n,i)=>i>start&&n.kind==='divider'):-1;
    if(start>=0&&end>start){
      const props={values,onChange,onClick,onUpload,busy,editTable};
      return <>
        <Nodes nodes={nodes.slice(0,start)} {...props}/>
        <details className="auto-fuel-expander" key="auto-fuel-expander">
          <summary>Registra carburante</summary>
          <Nodes nodes={nodes.slice(start+1,end)} {...props}/>
        </details>
        <Nodes nodes={nodes.slice(end)} {...props}/>
      </>;
    }
  }
  return nodes.map(n=>{
    if(n.key==='fatturato_lordo_originale')return null;
    if(n.kind==='caption'&&n.label?.startsWith('Importi fatturati IVA esclusa.')&&(values.schede_principali||'Fatturato')==='Fatturato'&&Number(values.anno_fiscale_selezionato)!==2026)return <p className="caption" key={n.key||n.label}>Inserisci gli importi IVA compresa cliccando sulle celle. Il gestionale scorpora il 22%; la tabella e i riepiloghi mostrano il fatturato IVA esclusa. Un mese mancante è distinto da zero.</p>;
    if(values.schede_principali==='Accantonamenti'&&(n.key==='accantonamenti_mese'||['#### Inserisci o modifica le provvigioni nette','#### Aggiungi o modifica un accantonamento'].includes(n.label)||(n.kind==='form'&&n.children?.some(c=>['Salva provvigioni nette','Salva accantonamento'].includes(c.label)))||(n.kind==='checkbox'&&n.label?.startsWith("Confermo l'eliminazione"))||['Elimina provvigioni nette del mese','Elimina accantonamento del mese'].includes(n.label)||(n.kind==='info'&&n.label?.startsWith('Anno 2026 in regime forfettario: i prospetti IVA ordinari'))))return null;
    if(values.schede_principali==='Auto'&&(n.label==='Limite chilometrico e penale'||(n.kind==='write'&&n.label?.startsWith('**Limite annuo:'))||(n.kind==='caption'&&(n.label?.startsWith('La penale è')||n.label?.startsWith('Nessun limite e nessuna tariffa')))))return null;
    if(values.schede_principali==='Costi'&&Number(values.anno_fiscale_selezionato)===2026&&(n.label==='Spesa effettiva da registrare o modificare'||(n.kind==='form'&&n.children?.some(c=>c.kind==='button'&&c.label==='Conferma spesa effettiva'))))return null;
    if(values.schede_principali==='Auto'&&n.kind==='selectbox'&&n.label==='Che cosa vuoi registrare o modificare?')return null;
    // Keep the original engine form available to the cell dialog, without rendering the old entry section.
    if(n.kind==='expander'&&['Elimina un importo registrato','Elimina manualmente un importo','Modifica una stima annuale importata dal file'].includes(n.label))return null;
    if(n.label==='**Inserisci o modifica un mese**'||['fatturato_mandante','fatturato_mese'].includes(n.key)||(n.kind==='caption'&&n.label?.startsWith('Mese già registrato: salvando sostituisci'))||(n.kind==='form'&&n.children?.some(c=>c.kind==='text_input'&&c.label==='Importo fatturato (IVA esclusa)')))return null;
    const children=<Nodes nodes={n.children} values={values} onChange={onChange} onClick={onClick} onUpload={onUpload} busy={busy} editTable={editTable}/>;
    const value=values[n.key]??n.value;
    const change=v=>onChange(n.key,v);
    let el;
    switch(n.kind){
      case 'title':el=n.label==='Gestionale Partita IVA'?null:<h1>{n.label}</h1>;break;
      case 'subheader':el=<h2>{values.schede_principali==='Auto'&&n.label==='Registra o modifica le spese'?'Registra carburante':n.label}</h2>;break;
      case 'caption':el=<p className="caption">{values.schede_principali==='Auto'&&n.label?.startsWith('Inserisci qui i chilometri mensili oppure una singola spesa di carburante')?'Registra qui ogni singola transazione di carburante. Percorrenza, autostrada e rate auto si modificano direttamente nella tabella sottostante.':n.label}</p>;break;
      case 'markdown':el=<Markdown text={n.label}/>;break;
      case 'write':case 'code':el=<p style={{whiteSpace:'pre-wrap'}}>{n.label}</p>;break;
      case 'info':case 'warning':case 'error':case 'success':el=<p role={n.kind==='error'?'alert':undefined} className={`notice ${n.kind}`}>{n.label}</p>;break;
      case 'table':el=<Table records={n.records} editTable={editTable}/>;break;
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
  const [editor,setEditor]=useState(null),[editorValue,setEditorValue]=useState(''),[editorError,setEditorError]=useState(''),[editorConfirmed,setEditorConfirmed]=useState(false);
  const worker=useRef(),tables=useRef(),pending=useRef(new Map()),seq=useRef(0),epoch=useRef(0);
  const currentValues=useRef({});
  const [uploadPage,setUploadPage]=useState(false);
  useEffect(()=>{
    worker.current=new Worker(new URL('./engine.worker.js',import.meta.url),{type:'module'});
    worker.current.onmessage=({data})=>{const p=pending.current.get(data.id);pending.current.delete(data.id);if(data.error)p?.reject(Error(data.error));else p?.resolve(data.result);};
    return()=>worker.current.terminate();
  },[]);
  useEffect(()=>{
    if(!client)return;
    return watchSession(client.auth,session=>{
      setUploadPage(false);setEditor(null);setEditorValue('');setEditorError('');setEditorConfirmed(false);
      worker.current?.postMessage({id:++seq.current,request:{operation:'clear_session'}});
      epoch.current++;tables.current=null;currentValues.current={};
      setBusy(false);setValues({});setResult(null);setUser(session?.user??null);
    });
  },[]);
  async function load(){
    const ticket=epoch.current;
    if(!client){tables.current=await (await fetch('/demo.json')).json();return;}
    const schema=await (await fetch('/schema.json')).json();
    const names=[...schema.tables.map(t=>t.name),...['sales_vat_invoices','vat_periods','pension_payments','purchase_cost_links','invoice_imports']];
    const pairs=await Promise.all(names.map(async name=>[name,await readTable(client,name)]));
    if(ticket!==epoch.current)throw Error('Sessione cambiata durante la lettura.');
    tables.current=Object.fromEntries(pairs);
  }
  async function run(event,inputs=currentValues.current){
    const ticket=epoch.current;setBusy(true);setError('');
    try{
      if(!tables.current)await load();
      const evaluate=()=>new Promise((resolve,reject)=>{const id=++seq.current;pending.current.set(id,{resolve,reject});worker.current.postMessage({id,request:{tables:tables.current,user,event,inputs}});});
      let next=await evaluate();
      const forceFuel=async current=>{
        const autoKey=Object.keys(current?.inputs||{}).find(key=>key.startsWith('auto_tipo_'));
        const page=current?.inputs?.schede_principali??inputs?.schede_principali;
        if(event===null&&page==='Auto'&&autoKey&&current.inputs[autoKey]!=='carburante'){
          inputs={...current.inputs,[autoKey]:'carburante'};
          return await evaluate();
        }
        return current;
      };
      next=await forceFuel(next);const didSave=next.mutations.length>0;
      if(ticket!==epoch.current)return;
      if(next.mutations.length){
        if(client){await applyMutations(client,next.mutations);await load();}
        else tables.current=next.tables;
        inputs=next.inputs;event=null;next=await evaluate();next=await forceFuel(next);
      }
      if(ticket===epoch.current){setResult(next);currentValues.current=next.inputs;setValues(next.inputs);return {next,saved:didSave};}
    }catch(e){if(ticket===epoch.current)setError(e.message);}
    finally{if(ticket===epoch.current)setBusy(false);}
  }
  useEffect(()=>{if(user)run(null);},[user]);
  async function openRevenue(cell){
    setEditorError('');setEditorConfirmed(false);
    const auto=cell.kind?.startsWith('auto-');
    const raw=cell.record?(cell.kind==='reserve'?cell.record[cell.field]:cell.kind==='cost'?cell.record.estimated_gross_amount:cell.kind==='auto-distance'?cell.record.distance_km:auto?cell.record.gross_amount:cell.record.amount):'';
    setEditorValue(String(!cell.kind&&cell.year!==2026?grossForRecord(cell.record):raw??'').replace('.',','));setEditor(cell);
    if(auto||cell.kind==='reserve')return;
    if(cell.ordinary){
      await run(cell.record?null:`costi_aggiungi_${cell.code}`,{...currentValues.current,...(cell.record?{costi_modifica_selezione:cell.selection}:{})});
      return;
    }
    await run(null,cell.kind==='cost'?{...currentValues.current,[`forfettario_stima_${cell.yearId}`]:cell.record.id}:{...currentValues.current,fatturato_mandante:cell.name,fatturato_mese:cell.monthName});
  }
  function editTable(records,column,index,open=false){
    if(busy)return null;
    const page=values.schede_principali||'Fatturato';
    const cell=page==='Fatturato'?revenueCell(records,column,index,tables.current,values.anno_fiscale_selezionato):page==='Costi'?costCell(records,column,index,tables.current,values.anno_fiscale_selezionato):page==='Accantonamenti'?reserveCell(records,column,index,tables.current,values.anno_fiscale_selezionato):page==='Auto'?autoCell(records,column,index,tables.current,values.anno_fiscale_selezionato):null;
    if(open&&cell?.editable)openRevenue(cell);
    return cell;
  }
  function flatten(nodes){return (nodes||[]).flatMap(n=>[n,...flatten(n.children)]);}
  function decimalValue(raw,max){
    let text=String(raw??'').trim().replace(/\s/g,'');
    if(!text)throw Error('Inserisci un valore.');
    if(text.includes(','))text=text.replace(/\./g,'').replace(',','.');
    if(!/^\d+(?:\.\d{1,2})?$/.test(text))throw Error('Inserisci un numero con al massimo due decimali.');
    const value=Number(text);
    if(!Number.isFinite(value)||value<0||value>max)throw Error('Valore non valido.');
    return value.toFixed(2);
  }
  function applyLocalMutation(mutation){
    const rows=tables.current[mutation.table]||(tables.current[mutation.table]=[]);
    if(mutation.operation==='insert'){
      rows.push({id:crypto.randomUUID(),user_id:user?.id,...mutation.payload});
      return;
    }
    const matches=row=>mutation.filters.every(([key,value])=>String(row[key])===String(value));
    const indexes=rows.map((row,index)=>matches(row)?index:-1).filter(index=>index>=0);
    if(indexes.length!==mutation.expected_rows)throw Error('Salvataggio non confermato o dati modificati altrove: aggiorna prima di riprovare.');
    if(mutation.operation==='update')rows[indexes[0]]={...rows[indexes[0]],...mutation.payload};
  }
  async function persistAutoCell(){
    if(client)await load();
    const fy=(tables.current.fiscal_years||[]).find(f=>f.id===editor.yearId);
    if(fy?.status!=='open')throw Error('Anno chiuso: importi in sola lettura.');
    const vehicles=tables.current.vehicles||[];
    if(vehicles.length!==1||vehicles[0].id!==editor.vehicleId)throw Error('Auto associata cambiata: annulla e riapri la cella.');
    const now=new Date();
    if(editor.year>now.getFullYear()||(editor.year===now.getFullYear()&&editor.month>now.getMonth()+1))throw Error('Non registrare come effettivo un mese futuro.');

    const isDistance=editor.kind==='auto-distance';
    const value=decimalValue(editorValue,isDistance?9999999999.99:999999999999.99);
    let mutation;
    if(isDistance){
      const rows=(tables.current.vehicle_monthly||[]).filter(r=>r.fiscal_year_id===editor.yearId&&r.vehicle_id===editor.vehicleId&&Number(r.month)===editor.month);
      if(rows.length!==(editor.record?1:0)||(editor.record&&(rows[0].id!==editor.record.id||String(rows[0].distance_km)!==String(editor.record.distance_km))))throw Error('Percorrenza modificata altrove: annulla e riapri la cella.');
      mutation=editor.record?{
        table:'vehicle_monthly',operation:'update',payload:{distance_km:value,notes:'Percorrenza effettiva dichiarata'},
        filters:[['id',editor.record.id],['fiscal_year_id',editor.yearId],['vehicle_id',editor.vehicleId],['month',editor.month],['distance_km',editor.record.distance_km]],expected_rows:1,
      }:{
        table:'vehicle_monthly',operation:'insert',payload:{fiscal_year_id:editor.yearId,vehicle_id:editor.vehicleId,month:editor.month,distance_km:value,notes:'Percorrenza effettiva dichiarata'},filters:[],expected_rows:1,result_ids:[crypto.randomUUID()],
      };
    }else{
      const rows=(tables.current.costs||[]).filter(r=>r.fiscal_year_id===editor.yearId&&r.vehicle_id===editor.vehicleId&&r.category_id===editor.category.id&&Number(String(r.expense_date).slice(5,7))===editor.month);
      if(rows.length!==(editor.record?1:0)||(editor.record&&(rows[0].id!==editor.record.id||String(rows[0].gross_amount)!==String(editor.record.gross_amount)||String(rows[0].expense_date)!==String(editor.record.expense_date))))throw Error('Importo modificato altrove: annulla e riapri la cella.');
      const date=`${editor.year}-${String(editor.month).padStart(2,'0')}-01`;
      const description=`${editor.kind==='auto-toll'?'Autostrada':'Rata auto'} · ${editor.monthName.toLowerCase()}`;
      mutation=editor.record?{
        table:'costs',operation:'update',payload:{gross_amount:value},
        filters:[['id',editor.record.id],['fiscal_year_id',editor.yearId],['category_id',editor.category.id],['vehicle_id',editor.vehicleId],['gross_amount',editor.record.gross_amount],['expense_date',editor.record.expense_date]],expected_rows:1,
      }:{
        table:'costs',operation:'insert',payload:{fiscal_year_id:editor.yearId,category_id:editor.category.id,vehicle_id:editor.vehicleId,expense_date:date,description,gross_amount:value,amount_includes_vat:true,vat_rate:editor.category.vat_rate,vat_deductible_rate:editor.category.vat_deductible_rate,cost_deductible_rate:editor.category.cost_deductible_rate,deductible_limit:editor.category.deductible_limit,fiscal_competence_year:editor.year,notes:'Spesa auto inserita manualmente; parametri fiscali da verificare'},filters:[],expected_rows:1,result_ids:[crypto.randomUUID()],
      };
    }
    if(client){await applyMutations(client,[mutation]);await load();}else applyLocalMutation(mutation);
    await run(null);setEditor(null);
  }
  async function saveRevenue(e){
    e.preventDefault();setEditorError('');setBusy(true);
    try{
      if(editor?.kind==='reserve'){
        if(client)await load();
        const value=decimalValue(editorValue,999999999999.99);
        const mutation=reserveMutation(editor,tables.current,value);
        if(client){await applyMutations(client,[mutation]);await load();}else applyLocalMutation(mutation);
        await run(null);setEditor(null);return;
      }
      if(editor?.kind?.startsWith('auto-')){await persistAutoCell();return;}
      if(client)await load();
      const fy=tables.current.fiscal_years.find(f=>f.id===editor.yearId);
      if(fy?.status!=='open')throw Error('Anno chiuso: importi in sola lettura.');
      const isCost=editor.kind==='cost';
      if(editor.ordinary){
        const cell=costCell([{Voce:editor.name,Registrato:'—','Da dedurre':'—','Totale annuo stimato':'—'}],'Totale annuo stimato',0,tables.current,editor.year);
        if(!cell||cell.record?.id!==editor.record?.id||String(cell.record?.estimated_gross_amount)!==String(editor.record?.estimated_gross_amount))throw Error('Importo modificato altrove: annulla e riapri la cella.');
        decimalValue(editorValue,999999999999.99);
        if(!editorConfirmed)throw Error('Conferma la modifica della stima annuale.');
        const nodes=flatten(result?.tree),field=nodes.find(n=>n.kind==='text_input'&&n.label===(editor.record?'Nuovo importo lordo (€)':'Importo lordo (€), IVA compresa se prevista'));
        const submit=nodes.find(n=>n.kind==='button'&&n.label===(editor.record?'Salva modifica':'Salva nuova voce'));
        if(!field||!submit)throw Error('Modulo non disponibile: annulla e riapri la cella.');
        const saved=await run(submit.key,{...currentValues.current,[field.key]:editorValue});
        if(saved?.saved)setEditor(null);
        else setEditorError(flatten(saved?.next?.tree).filter(n=>['warning','error'].includes(n.kind)).map(n=>n.label).join(' ')||'Salvataggio non confermato.');
        return;
      }
      const rows=isCost?(tables.current.annual_cost_estimates||[]).filter(r=>r.fiscal_year_id===editor.yearId&&r.id===editor.record.id):tables.current.monthly_revenues.filter(r=>r.fiscal_year_id===editor.yearId&&r.principal_id===editor.principalId&&Number(r.month)===editor.month);
      if(rows.length>1||rows.length!==(editor.record?1:0)||(editor.record&&(rows[0].id!==editor.record.id||String(isCost?rows[0].estimated_gross_amount:rows[0].amount)!==String(isCost?editor.record.estimated_gross_amount:editor.record.amount))))throw Error('Importo modificato altrove: annulla e riapri la cella.');
      const nodes=flatten(result?.tree),field=nodes.find(n=>n.kind==='text_input'&&n.label===(isCost?'Nuovo importo annuo (€)':'Importo fatturato (IVA esclusa)')),submit=nodes.find(n=>n.kind==='button'&&n.label===(isCost?'Salva stima':'Salva importo'));
      const confirmation=isCost?nodes.find(n=>n.kind==='checkbox'&&n.label==='Confermo la modifica della stima annuale'):null;
      if(!field||!submit)throw Error('Modulo non disponibile: annulla e riapri la cella.');
      if(isCost&&!confirmation)throw Error('Conferma non disponibile: annulla e riapri la cella.');
      const selection=isCost?{[`forfettario_stima_${editor.yearId}`]:editor.record.id,[confirmation.key]:editorConfirmed}:{fatturato_mandante:editor.name,fatturato_mese:editor.monthName};
      const saved=await run(submit.key,{...currentValues.current,anno_fiscale_selezionato:editor.year,...selection,[field.key]:!isCost&&editor.year!==2026?splitGross(editorValue).net:editorValue,fatturato_lordo_originale:!isCost&&editor.year!==2026?splitGross(editorValue).gross:''});
      if(saved?.saved)setEditor(null);
      else setEditorError(flatten(saved?.next?.tree).filter(n=>['warning','error'].includes(n.kind)).map(n=>n.label).join(' ')||'Salvataggio non confermato. Controlla l’importo.');
    }catch(e){setEditorError(e.message);}finally{setBusy(false);}
  }
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
  async function exportBackup(){
    const ticket=epoch.current,savedInputs={...currentValues.current,schede_principali:currentValues.current.schede_principali||'Fatturato'};setBusy(true);setError('');
    const evaluate=inputs=>new Promise((resolve,reject)=>{const id=++seq.current;pending.current.set(id,{resolve,reject});worker.current.postMessage({id,request:{tables:tables.current,user,event:null,inputs}});});
    try{
      if(client)await load();
      const {BACKUP_PAGES,backupBytes}=await import('./excel-backup.js');
      const year=savedInputs.anno_fiscale_selezionato,views={};
      for(const page of BACKUP_PAGES){views[page]=await evaluate({...savedInputs,schede_principali:page});if(views[page].mutations.length)throw Error('Backup interrotto: il prospetto richiede un salvataggio.');}
      const bytes=await backupBytes({year,tables:tables.current,views});
      if(ticket!==epoch.current)return;
      const url=URL.createObjectURL(new Blob([bytes],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}));
      const a=document.createElement('a');a.href=url;a.download='backup_partita_iva_'+year+'_'+new Date().toISOString().slice(0,10)+'.xlsx';a.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
    }catch(e){if(ticket===epoch.current)setError('Backup non creato: '+e.message);}
    finally{if(ticket===epoch.current){try{const restored=await evaluate(savedInputs);setResult(restored);currentValues.current=restored.inputs;setValues(restored.inputs);}finally{setBusy(false);}}}
  }
  async function login(e){e.preventDefault();setBusy(true);setError('');const f=new FormData(e.target);const {error}=await client.auth.signInWithPassword({email:String(f.get('email')).trim(),password:String(f.get('password'))});e.target.reset();setBusy(false);if(error)setError('Accesso non riuscito. Controlla le credenziali.');}
  const page=uploadPage?'Carica fattura':values.schede_principali||'Fatturato';
  async function importInvoice(payload){
    if(!client)throw Error('Il collaudo non registra fatture reali.');
    const ticket=epoch.current;
    const {data:identity,error:authError}=await client.auth.getUser();
    if(authError||!identity?.user||ticket!==epoch.current)throw Error('Sessione scaduta: accedi nuovamente.');
    const {data,error:saveError}=await client.rpc('piva_import_invoice',{p:payload});
    if(saveError){await load();throw Error(saveError.code==='23505'?'Fattura già registrata: aggiorna i dati e controlla.':saveError.message);}
    if(!data||ticket!==epoch.current)throw Error('Salvataggio da verificare: aggiorna prima di riprovare.');
    await load();await run(null);
  }
  const inspectInvoice=request=>new Promise((resolve,reject)=>{const id=++seq.current;pending.current.set(id,{resolve,reject});worker.current.postMessage({id,request});});
  let vatPreview=null;
  if(editor&&!editor.kind&&editor.year!==2026){try{vatPreview=splitGross(editorValue);}catch{}}
  return <div className="shell">{mobile&&<button className="backdrop" aria-label="Chiudi menu laterale" onClick={()=>setMobile(false)}/>}<aside inert={editor?'':undefined} aria-label="Menu principale" className={mobile?'sidebar shown':'sidebar'}><div className="brand"><div className="brand-icon"><Calculator/></div><div><strong>Gestionale</strong><small>Partita IVA · Personale</small></div><button className="side-close" aria-label="Chiudi menu" onClick={()=>setMobile(false)}><X size={18}/></button></div><div className="nav-label">IL TUO GESTIONALE</div><nav aria-label="Sezioni">{NAV.map((p,i)=><button key={p} className={page===p?'active':''} aria-current={page===p?'page':undefined} disabled={busy||!user} onClick={()=>{setUploadPage(false);change('schede_principali',p);setMobile(false);}}>{React.createElement(NAV_ICONS[i],{size:18,"aria-hidden":true})}<span>{p}</span></button>)}</nav><nav className="invoice-nav"><button className={uploadPage?"active":""} aria-current={uploadPage?"page":undefined} disabled={busy||!user} onClick={()=>{setUploadPage(true);setMobile(false);}}><Upload size={18}/><span>Carica fattura</span></button></nav><Nodes nodes={result?.sidebar.filter(n=>!['Utente autenticato',user?.email,'Esci'].includes(n.label))} values={values} onChange={change} onClick={event=>run(event)} onUpload={upload} busy={busy}/><footer><ShieldCheck size={16}/> {client?'Accesso protetto':'Collaudo isolato'}<small>{user?.email}</small></footer></aside><main inert={editor?'':undefined}><header className="page-header"><h1>{user?page:"Benvenuto"}</h1></header><button className="menu" onClick={()=>setMobile(!mobile)} aria-label="Apri menu"><Menu/></button><div className="top-actions">{user&&page==='Fatturato'&&<button disabled={busy||!result} onClick={exportBackup}>Scarica backup Excel</button>}{client&&user&&<button disabled={busy} onClick={async()=>{await client.auth.signOut({scope:'local'});}}>Esci</button>}</div>{error&&<p role="alert" className="notice error">{error}</p>}{!user?<form onSubmit={login} className="login"><h1>Accedi</h1><label>Email<input name="email" type="email" required autoComplete="username"/></label><label>Password<input name="password" type="password" required autoComplete="current-password"/></label><button disabled={busy}>Accedi</button></form>:<>{busy&&<p role="status">{result?'Aggiornamento…':'Preparazione del gestionale e del motore di calcolo…'}</p>}<div hidden={uploadPage}><EnasarcoContext.Provider value={page==='Fatturato'?enasarcoAlerts(tables.current,values.anno_fiscale_selezionato):[]}><Nodes nodes={result?.tree} values={values} onChange={change} onClick={event=>run(event)} onUpload={upload} busy={busy} editTable={editTable}/></EnasarcoContext.Provider><button disabled={busy} onClick={()=>run(null)}>Aggiorna prospetto</button></div><div hidden={!uploadPage}><InvoiceImport key={user.id} tables={tables.current||{}} inspect={inspectInvoice} onSave={importInvoice} onRefresh={async()=>{await load();await run(null);}} disabled={busy}/></div></>}</main>{editor&&<div className="modal-backdrop"><section className="amount-dialog" role="dialog" onKeyDown={e=>{if(e.key==='Escape'&&!busy)setEditor(null);}} aria-modal="true" aria-labelledby="amount-title"><form onSubmit={saveRevenue}><h2 id="amount-title">{editor.name}</h2><p>{editor.kind==='cost'?'Stima annua ·':editor.monthName} {editor.year}</p><label>{editor.kind==='reserve'?'Importo del mese (€)':editor.kind==='cost'?'Importo annuo lordo (€)':editor.kind==='auto-distance'?'Chilometri effettivi':editor.kind?.startsWith('auto-')?'Importo mensile lordo (€)':editor.year!==2026?'Importo fatturato (IVA compresa al 22%)':'Importo fatturato (IVA esclusa)'}<input autoFocus value={editorValue} onChange={e=>setEditorValue(e.target.value)} disabled={busy} inputMode="decimal"/></label>{!editor.kind&&editor.year!==2026&&<p className="notice info">{vatPreview?`Fatturato IVA esclusa: ${vatPreview.net.replace('.',',')} € · IVA 22%: ${vatPreview.vat.replace('.',',')} €`:'Inserisci il totale prima di eventuali trattenute Enasarco o ritenute.'}</p>}<p className="caption">{editor.kind==='cost'?'Il valore sostituisce la stima annuale e aggiorna i riepiloghi. Inserisci 0 per un importo nullo.':editor.kind==='auto-distance'?'Il valore sostituisce la percorrenza del mese. Inserisci 0 se il mese è realmente a zero.':editor.kind?.startsWith('auto-')?'Il valore sostituisce l’importo del mese e aggiorna automaticamente riepiloghi e stima annua. Inserisci 0 se il mese è realmente a zero.':'Il valore sostituisce quello della cella. Inserisci 0 per un mese a zero; una cella vuota non è ancora compilata.'}</p>{editor.kind==='cost'&&<label className="check"><input type="checkbox" checked={editorConfirmed} disabled={busy} onChange={e=>setEditorConfirmed(e.target.checked)}/>Confermo la modifica della stima annuale</label>}{editorError&&<p role="alert" className="notice error">{editorError}</p>}<div className="dialog-actions"><button type="button" disabled={busy} onClick={()=>setEditor(null)}>Annulla</button><button className="primary" type="submit" disabled={busy}>{busy?'Salvataggio…':'Salva importo'}</button></div></form></section></div>}</div>;
}
createRoot(document.getElementById('root')).render(<App/>);
