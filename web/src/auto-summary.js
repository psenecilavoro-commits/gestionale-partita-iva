const COLUMNS=['Percorrenza','Carburante','Autostrada','Rate auto'];
export function autoSummary(records){
 if(!Array.isArray(records)||records.length<14||records[12]?.Mese!=='Totale registrato'||!COLUMNS.every(c=>Object.hasOwn(records[0],c)))return records;
 const mean={Mese:'Media mensile'};
 for(const column of COLUMNS){
  const values=records.slice(0,12).map(r=>String(r[column]??'—')).filter(v=>v!=='—');
  if(!values.length){mean[column]='—';continue;}
  const total=values.reduce((sum,text)=>{const n=text.replace(/\s|€|km/g,'').replace(/\./g,'').replace(',','.');if(!/^\d+(?:\.\d{1,2})?$/.test(n))throw Error('Valore del riepilogo Auto non valido');const [whole,fraction='']=n.split('.');return sum+BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'));},0n);
  const count=BigInt(values.length),rounded=(total*2n+count)/(count*2n);
  mean[column]=new Intl.NumberFormat('it-IT',{useGrouping:'always',minimumFractionDigits:column==='Percorrenza'?0:2,maximumFractionDigits:2}).format(Number(rounded)/100)+(column==='Percorrenza'?' km':' €');
 }
 return [...records.slice(0,13),mean,...records.slice(13)];
}
