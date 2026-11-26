export const GROUPS = [
 {title:'Anagrafica',fields:[['name','Denominazione'],['address','Indirizzo'],['vat','Partita IVA'],['taxCode','Codice fiscale']]},
 {title:'Fatturazione e contatti',fields:[['sdi','Codice destinatario SDI'],['pec','PEC'],['email','Email'],['phone','Telefono']]},
 {title:'Coordinate bancarie',option:'bank',fields:[['holder','Intestatari del conto'],['bank','Banca'],['iban','IBAN'],['bic','BIC / SWIFT']]},
 {title:'Attività e previdenza',option:'extra',fields:[['ateco','Codice ATECO'],['inps','Posizione INPS'],['enasarco','Matricola Enasarco']]},
];
export function normalizeProfile(raw={}) {
 const result={};
 for(const {fields} of GROUPS)for(const [key,label] of fields){
  const value=String(raw[key]??'').trim();
  if(value.length>250||/[\x00-\x1f]/.test(value))throw Error(`${label}: inserisci un testo di massimo 250 caratteri su una riga.`);
  result[key]=value;
 }
 for(const key of ['vat','taxCode','sdi','iban','bic'])result[key]=result[key].replace(/\s/g,'').toUpperCase();
 if(!result.name)throw Error('Inserisci la denominazione.');
 if(result.iban){
  if(!/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(result.iban))throw Error('IBAN non valido.');
  const text=(result.iban.slice(4)+result.iban.slice(0,4)).replace(/[A-Z]/g,c=>String(c.charCodeAt(0)-55));
  let mod=0;for(const digit of text)mod=(mod*10+Number(digit))%97;
  if(mod!==1)throw Error('Il codice di controllo dell’IBAN non è valido.');
 }
 return result;
}
export function sharingGroups(profile,options={}) {
 return GROUPS.filter(g=>!g.option||options[g.option]).map(g=>({...g,fields:g.fields.filter(([key])=>profile[key])})).filter(g=>g.fields.length);
}
export function billingText(profile) {
 return sharingGroups(profile).flatMap(g=>g.fields.map(([key,label])=>`${label}: ${profile[key]}`)).join('\n');
}
// A4 PDF, Helvetica WinAnsi; byte offsets refer to the final single-byte stream.
export function profilePDF(profile,options={}) {
 const escape=s=>String(s).replace(/[\u2018\u2019]/g,"'").replace(/[\u2013\u2014]/g,'-').replace(/[^\x20-\xff]/g,'?').replace(/[\\()]/g,'\\$&');
 const pages=[];let commands=[],y=760;
 const text=(s,size=11,bold=false,color='0.18 0.27 0.32')=>{commands.push(`${color} rg BT /${bold?'F2':'F1'} ${size} Tf 48 ${y} Td (${escape(s)}) Tj ET`);};
 const start=()=>{commands=[];y=785;text('DATI AZIENDALI',20,true);y-=32;};
 const finish=()=>{commands.push('0.82 0.86 0.88 RG 48 44 m 547 44 l S');pages.push(commands.join('\n'));};
 start();
 for(const group of sharingGroups(profile,options)){
  if(y<130){finish();start();}
  text(group.title,12,true);y-=22;
  for(const [key,label] of group.fields){
   const words=String(profile[key]).split(/\s+/);const lines=[];let line='';
   for(let word of words){while(word.length>72){if(line){lines.push(line);line='';}lines.push(word.slice(0,72));word=word.slice(72);}if((line+' '+word).trim().length>72){lines.push(line);line=word;}else line=(line+' '+word).trim();}
   if(line)lines.push(line);
   if(y<65+lines.length*15){finish();start();}
   text(label,9,false,'0.40 0.48 0.52');y-=15;
   for(const item of lines){text(item);y-=15;}y-=9;
  }
  y-=13;
 }
 finish();
 const objects=['<< /Type /Catalog /Pages 2 0 R >>','', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>','<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>'];const kids=[];
 for(const content of pages){const id=objects.length+1;kids.push(`${id} 0 R`);objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${id+1} 0 R >>`);objects.push(`<< /Length ${content.length} >>\nstream\n${content}\nendstream`);}
 objects[1]=`<< /Type /Pages /Kids [${kids.join(' ')}] /Count ${pages.length} >>`;
 let pdf='%PDF-1.4\n',offsets=[0];for(let i=0;i<objects.length;i++){offsets.push(pdf.length);pdf+=`${i+1} 0 obj\n${objects[i]}\nendobj\n`;}
 const xref=pdf.length;pdf+=`xref\n0 ${objects.length+1}\n0000000000 65535 f \n`;for(const offset of offsets.slice(1))pdf+=String(offset).padStart(10,'0')+' 00000 n \n';pdf+=`trailer\n<< /Size ${objects.length+1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
 return Uint8Array.from(pdf,c=>c.charCodeAt(0));
}
export async function saveProfile(client,userId,previous,raw) {
 const data=normalizeProfile(raw);
 let query=previous?client.from('company_profiles').update({data}).eq('id',previous.id).eq('user_id',userId).eq('updated_at',previous.updated_at):client.from('company_profiles').insert({user_id:userId,data});
 const {data:rows,error}=await query.select();
 if(error)throw Error(error.message);
 if(rows?.length!==1)throw Error('Dati modificati altrove: ricarica la scheda prima di riprovare.');
 return rows[0];
}
