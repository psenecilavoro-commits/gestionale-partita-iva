export function isPrincipalSummary(records){
 return Array.isArray(records)&&records.length>0&&records.every(r=>['Mandante','Mesi compilati','Fatturato','Media mesi compilati','Stima annua'].every(k=>Object.hasOwn(r,k)));
}
export function principalYear(tables,year){
 const matches=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(year));
 if(matches.length!==1||matches[0].status!=='open')throw Error('Seleziona un anno fiscale aperto.');
 return matches[0];
}
export function principalCreate(tables,rawName,year){
 principalYear(tables,year);
 const name=String(rawName??'').normalize('NFC').trim().replace(/\s+/g,' ');
 if(!name||name.length>120)throw Error('Inserisci un nome da 1 a 120 caratteri.');
 if(['mese','totale mese'].includes(name.toLocaleLowerCase('it')))throw Error('Scegli un nome diverso dalle intestazioni della tabella.');
 if((tables.principals||[]).some(p=>p.name.normalize('NFC').trim().replace(/\s+/g,' ').toLocaleLowerCase('it')===name.toLocaleLowerCase('it')))throw Error('Questa mandante è già presente.');
 return {table:'principals',operation:'insert',payload:{name,enasarco_relationship:'plurimandatario',active:true},filters:[],expected_rows:1};
}
export function principalDelete(tables,id,year){
 principalYear(tables,year);
 const rows=(tables.principals||[]).filter(p=>p.id===id);
 if(rows.length!==1)throw Error('Mandante non più disponibile: aggiorna il prospetto.');
 const links=[];
 for(const [table,label] of [['monthly_revenues','registrazioni di fatturato'],['sales_vat_invoices','fatture di vendita']]){
  const groups=new Map();
  for(const row of tables[table]||[])if(row.principal_id===id){
   const fy=(tables.fiscal_years||[]).find(y=>y.id===row.fiscal_year_id);
   const yearLabel=fy?.fiscal_year??'anno da verificare';groups.set(yearLabel,(groups.get(yearLabel)||0)+1);
  }
  for(const [yearLabel,count] of groups)links.push(`${yearLabel}: ${count} ${label}`);
 }
 if(links.length)throw Error('Rimozione bloccata. Dati collegati: '+links.join('; ')+'. Nessun dato eliminato.');
 const row=rows[0];
 return {table:'principals',operation:'delete',filters:[['id',id],['user_id',row.user_id],['name',row.name]],expected_rows:1};
}
