import React from 'react';
import {enasarcoAlerts} from './enasarco-alerts.js';
const euro=cents=>new Intl.NumberFormat('it-IT',{style:'currency',currency:'EUR'}).format(Number(cents)/100);
export function EnasarcoNotice({tables,year}){
  const rows=enasarcoAlerts(tables,year);
  if(!rows.length)return null;
  return <section className="card" aria-label="Controllo massimale Enasarco"><h2>Massimale Enasarco · {year}</h2><p className="caption">Controllo per mandante sul fatturato registrato IVA esclusa. La previsione annua non determina il superamento.</p>{rows.map((r,index)=><div key={index} className={`notice ${['stop','reached'].includes(r.status)?'warning':'info'}`}>
    <strong>{r.name}</strong>{r.status==='missing'?<p>Massimale o rapporto Enasarco non configurato: completa i parametri nella scheda Imposte.</p>:r.status==='invalid'?<p>Controllo non disponibile: verifica le registrazioni del fatturato.</p>:<><p>{r.status==='stop'?'STOP · Massimale superato':r.status==='reached'?'Massimale raggiunto':r.status==='empty'?'Nessun fatturato registrato':'VAI · Massimale non ancora raggiunto'} · Registrato: {euro(r.total)} · Massimale: {euro(r.limit)}{r.remaining>0n?` · Residuo: ${euro(r.remaining)}`:''}</p>{['stop','reached'].includes(r.status)&&<p>Promemoria: non applicare la trattenuta Enasarco alle provvigioni successive al massimale di questa mandante. Se una fattura attraversa la soglia, verifica la quota residua soggetta a contribuzione.</p>}{r.provisional&&<p>Il massimale configurato è provvisorio: confermalo per l’anno prima di usare questo promemoria per la fatturazione.</p>}</>}
  </div>)}</section>;
}
