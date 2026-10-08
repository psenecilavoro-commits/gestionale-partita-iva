import React,{useState,useRef} from 'react';
import {prepareDocument} from './documents.js';
import {parseInvoiceXML,parseInvoiceText,planInvoice,suggestCategory,cents,money,todayISO} from './invoice-import.js';

export default function InvoiceImport({tables={},inspect,onSave,onRefresh,disabled}){
 const [direction,setDirection]=useState('ricevuta'),[paymentDate,setPaymentDate]=useState(''),[invoice,setInvoice]=useState(null),[fileName,setFileName]=useState(''),[error,setError]=useState(''),[reading,setReading]=useState(false),[saved,setSaved]=useState(''),[confirmed,setConfirmed]=useState(false);
 const [categoryId,setCategoryId]=useState(''),[principalId,setPrincipalId]=useState(''),[receivedDate,setReceivedDate]=useState(''),[registeredDate,setRegisteredDate]=useState(todayISO()),[deductibleVat,setDeductibleVat]=useState('');
 const input=useRef(),generation=useRef(0);
 const date=paymentDate||invoice?.invoiceDate||todayISO(),year=(tables.fiscal_years||[]).find(y=>Number(y.fiscal_year)===Number(date.slice(0,4)));
 const categories=(tables.cost_categories||[]).filter(c=>c.fiscal_year_id===year?.id);
 const subjectKey=direction==='ricevuta'?'supplier':'customer';
 const options={direction,paymentDate,categoryId,principalId,receivedDate,registeredDate,deductibleVat};
 let plan=null,problem='';if(invoice){try{plan=planInvoice(invoice,options,tables);}catch(e){problem=e.message;}}
 const reset=()=>{generation.current++;setInvoice(null);setConfirmed(false);setError('');setFileName('');if(input.current)input.current.value='';};
 const edit=(key,value)=>{setConfirmed(false);setInvoice(old=>({...old,[key]:value}));};
 async function read(file){
  if(!file)return;const ticket=++generation.current;setReading(true);setError('');setSaved('');setConfirmed(false);setInvoice(null);
  try{
   if(!file.size||file.size>8*1024*1024)throw Error('Scegli un documento fino a 8 MB.');
   const extension=file.name.toLowerCase().split('.').pop();let parsed;
   if(extension==='xml')parsed=parseInvoiceXML(await file.text());
   else{
    const bytes=new Uint8Array(await file.arrayBuffer());let binary='';for(let i=0;i<bytes.length;i+=8192)binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    const prepared=await prepareDocument(file,btoa(binary),inspect,false);parsed=parseInvoiceText(prepared.document_text||'');
   }
   if(ticket!==generation.current)return;
   const paymentYear=(tables.fiscal_years||[]).find(y=>Number(y.fiscal_year)===Number((paymentDate||parsed.invoiceDate).slice(0,4)));
   const annualCategories=(tables.cost_categories||[]).filter(c=>c.fiscal_year_id===paymentYear?.id);
   const suggested=suggestCategory(parsed,annualCategories);
   setCategoryId(suggested);
   const suggestedCategory=annualCategories.find(c=>c.id===suggested);
   try{const vat=parsed.groups.reduce((sum,g)=>sum+cents(g.vat),0n);setDeductibleVat(suggestedCategory?money((vat*BigInt(Math.round(Number(suggestedCategory.vat_deductible_rate||0)*10000))+5000n)/10000n):'');}catch{setDeductibleVat('');}
   setPrincipalId((tables.principals||[]).find(p=>p.name.toLowerCase()===parsed.customer.name.toLowerCase())?.id||'');
   setReceivedDate(parsed.receivedDate||parsed.invoiceDate);setRegisteredDate(todayISO());setInvoice(parsed);setFileName(file.name);
  }catch(e){if(ticket===generation.current)setError(e.message);}finally{if(ticket===generation.current)setReading(false);}
 }
 function category(value){setCategoryId(value);setConfirmed(false);const selected=categories.find(c=>c.id===value);try{const vat=(invoice?.groups||[]).reduce((sum,g)=>sum+cents(g.vat),0n);setDeductibleVat(money((vat*BigInt(Math.round(Number(selected?.vat_deductible_rate||0)*10000))+5000n)/10000n));}catch{setDeductibleVat('');}}
 async function save(e){e.preventDefault();if(!plan||!confirmed||reading)return;setReading(true);setError('');try{await onSave(plan.payload);setSaved(`Fattura ${invoice.number} importata. Le registrazioni e i riepiloghi sono aggiornati.`);reset();}catch(e){setError(e.message);}finally{setReading(false);}}
 const busy=reading||disabled;
 return <section className="card invoice-import"><h2>Carica fattura</h2><p className="caption">Seleziona un documento, controlla l’anteprima e conferma. Il file viene letto sul tuo dispositivo; il documento non viene conservato.</p>
  <div className="invoice-grid"><label>Tipo di fattura<select value={direction} disabled={busy} onChange={e=>{setDirection(e.target.value);setConfirmed(false);}}><option value="ricevuta">Ricevuta</option><option value="emessa">Emessa</option></select></label><label>Data di pagamento / incasso (facoltativa)<input type="date" max={todayISO()} value={paymentDate} disabled={busy} onChange={e=>{setPaymentDate(e.target.value);setCategoryId('');setConfirmed(false);}}/></label></div>
  <p className="caption">Se la data è vuota, assumiamo pagamento o incasso alla data di emissione. Per ora è prevista una fattura interamente pagata, senza pagamenti parziali.</p>
  <label>Fattura XML, PDF o immagine<input ref={input} type="file" accept=".xml,.pdf,.png,.jpg,.jpeg" disabled={busy} onChange={e=>read(e.target.files[0])}/></label>
  {reading&&<p role="status">{invoice?'Registrazione…':'Lettura del documento…'}</p>}{error&&<p role="alert" className="notice error">{error}</p>}{saved&&<p role="status" className="notice success">{saved}</p>}
  {invoice&&<form onSubmit={save}><h3>Anteprima · {fileName}</h3><p className="notice info">{invoice.source==='XML'?'Dati letti dall’XML: verifica categoria, date e trattamento IVA.':'Lettura assistita del documento: completa e controlla tutti i dati prima di confermare. Il 22% eventualmente proposto va verificato sulla fattura.'}</p>
   <div className="invoice-grid"><label>{direction==='ricevuta'?'Fornitore':'Cliente / mandante'}<input value={invoice[subjectKey].name} disabled={busy} onChange={e=>edit(subjectKey,{...invoice[subjectKey],name:e.target.value})}/></label><label>Partita IVA / codice fiscale<input value={invoice[subjectKey].taxId} disabled={busy} onChange={e=>edit(subjectKey,{...invoice[subjectKey],taxId:e.target.value})}/></label><label>Numero fattura<input value={invoice.number} disabled={busy} onChange={e=>edit('number',e.target.value)}/></label><label>Data di emissione<input type="date" max={todayISO()} value={invoice.invoiceDate} disabled={busy} onChange={e=>{edit('invoiceDate',e.target.value);setCategoryId('');}}/></label></div>
   {direction==='ricevuta'?<><label>Categoria della spesa<select value={categoryId} disabled={busy} onChange={e=>category(e.target.value)}><option value="">Seleziona la categoria</option>{categories.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label><div className="invoice-grid"><label>Data di ricezione<input type="date" max={todayISO()} value={receivedDate} disabled={busy} onChange={e=>{setReceivedDate(e.target.value);setConfirmed(false);}}/></label><label>Data di registrazione IVA<input type="date" max={todayISO()} value={registeredDate} disabled={busy} onChange={e=>{setRegisteredDate(e.target.value);setConfirmed(false);}}/></label></div><label>IVA effettivamente detraibile verificata (€)<input inputMode="decimal" value={deductibleVat} disabled={busy} onChange={e=>{setDeductibleVat(e.target.value);setConfirmed(false);}}/></label><p className="caption">La categoria propone la percentuale già configurata. Verifica che sia applicabile a tutte le voci della fattura. Nel 2026 non viene registrata IVA detraibile. L’IVA è attribuita al mese di registrazione, senza anticipazione automatica.</p></>:<label>Mandante<select value={principalId} disabled={busy} onChange={e=>{setPrincipalId(e.target.value);setConfirmed(false);}}><option value="">Seleziona la mandante</option>{(tables.principals||[]).map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label>}
   {invoice.lines.length>0&&<details><summary>Voci del documento</summary><ul>{invoice.lines.map((l,i)=><li key={i}>{l.description} · {l.amount} € · IVA {l.rate}% {l.nature}</li>)}</ul></details>}
   <h3>Riepilogo IVA</h3>{invoice.groups.map((group,index)=><div className="invoice-grid invoice-vat-row" key={index}>{[['base','Imponibile / escluso (€)'],['vat','IVA (€)'],['rate','Aliquota (%)'],['nature','Natura (se senza IVA)']].map(([key,label])=><label key={key}>{label}<input value={group[key]} disabled={busy} onChange={e=>edit('groups',invoice.groups.map((g,i)=>i===index?{...g,[key]:e.target.value}:g))}/></label>)}</div>)}
   <button type="button" disabled={busy||invoice.groups.length>=30} onClick={()=>edit('groups',[...invoice.groups,{base:'',vat:'',rate:'22',nature:'',payability:'I'}])}>Aggiungi voce al riepilogo IVA</button>
   <label>Totale documento prima delle trattenute (€)<input inputMode="decimal" value={invoice.total} disabled={busy} onChange={e=>edit('total',e.target.value)}/></label>
   <h3>Destinazioni</h3>{problem?<p className="notice warning">{problem}</p>:<><ul>{plan.destinations.map(d=><li key={d}>{d}</li>)}</ul>{plan.assumedPayment&&<p className="notice info">Data di pagamento / incasso assunta uguale all’emissione: {invoice.invoiceDate}.</p>}{direction==='ricevuta'&&Number(date.slice(0,4))!==2026&&<p className="caption">Le stime annuali restano separate dalle spese effettive. Se le voci hanno trattamenti diversi, il prospetto fiscale può richiedere una verifica prima di mostrare il risultato.</p>}</>}
   <label className="check"><input type="checkbox" checked={confirmed} disabled={busy||!plan} onChange={e=>setConfirmed(e.target.checked)}/>Confermo dati, date, trattamento IVA e che questi importi non siano già compresi nelle registrazioni manuali.</label>
   <div className="dialog-actions"><button type="button" disabled={busy} onClick={reset}>Annulla</button><button type="submit" className="primary" disabled={busy||!plan||!confirmed}>Conferma importazione</button></div>
  </form>}
  <button type="button" disabled={busy} onClick={onRefresh}>Aggiorna dati</button>
 </section>;
}
