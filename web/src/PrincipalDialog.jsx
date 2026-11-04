import React,{useEffect,useRef} from 'react';
export default function PrincipalDialog({principal,busy,name,setName,error,onSubmit,onClose}){
 const section=useRef();
 useEffect(()=>{const previous=document.activeElement;return()=>queueMicrotask(()=>previous?.focus());},[]);
 const removing=principal.mode==='delete';
 function keys(e){
  if(e.key==='Escape'&&!busy){e.preventDefault();onClose();}
  if(e.key==='Tab'){
   const controls=[...section.current.querySelectorAll('button:not(:disabled),input:not(:disabled)')];
   const first=controls[0],last=controls.at(-1);
   if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}
   else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}
  }
 }
 return <div className="modal-backdrop"><section ref={section} className="amount-dialog" role="dialog" aria-modal="true" aria-labelledby="principal-title" onKeyDown={keys}><form onSubmit={onSubmit}>
  <h2 id="principal-title">{removing?'Elimina mandante':'Aggiungi mandante'}</h2>
  {removing?<p>Confermi la rimozione di <strong>{principal.name}</strong> dall’anagrafica condivisa di tutti gli anni?</p>:<label>Nome della mandante<input autoFocus required maxLength={120} value={name} disabled={busy} onChange={e=>setName(e.target.value)} autoComplete="off"/></label>}
  {error&&<p className="notice error" role="alert">{error}</p>}
  <div className="dialog-actions"><button autoFocus={removing} type="button" disabled={busy} onClick={onClose}>Annulla</button><button type="submit" className="primary" disabled={busy}>{busy?'Attendi…':removing?'Elimina':'Aggiungi mandante'}</button></div>
 </form></section></div>;
}
