import JSZip from 'jszip';
export const digest=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(b=>b.toString(16).padStart(2,'0')).join('');
export function snapshot(tables,user,revision){
 if(!tables?.fiscal_years?.length||!user?.id)throw Error('Dati completi non ancora disponibili.');
 return {format:1,createdAt:new Date().toISOString(),revision,user:{id:user.id,email:user.email},tables:structuredClone(tables)};
}
export async function completeBackup({tables,user,revision,fetchFile=fetch,onProgress=()=>{}}){
 const response=await fetchFile('/backup-manifest.json',{cache:'no-store'});if(!response.ok)throw Error('Elenco dei file non disponibile.');
 const manifest=await response.json();if(manifest.format!==1||manifest.revision!==revision)throw Error('È disponibile una versione più recente: ricarica la pagina prima del backup.');
 if(!Array.isArray(manifest.files)||!['index.html','engine.json.gz','runtime/pyodide.mjs','restore-source.zip',...['LEGGIMI.txt','Avvia-offline.cmd','avvia-offline.ps1','ripristina-dati.py'].map(n=>'backup-support/'+n)].every(path=>manifest.files.some(f=>f.path===path)))throw Error('Elenco backup incompleto.');
 const zip=new JSZip(),data=snapshot(tables,user,revision),hashes={};let index=0;
 for(const file of manifest.files){
  if(!/^[\w./-]+$/.test(file.path)||file.path.includes('..'))throw Error('Percorso backup non valido.');
  const r=await fetchFile('/'+file.path,{cache:'no-store'});if(!r.ok)throw Error('File mancante: '+file.path);
  const bytes=new Uint8Array(await r.arrayBuffer());
  if(bytes.length!==file.size||await digest(bytes)!==file.sha256)throw Error('File cambiato o incompleto: '+file.path+'. Riprova dopo aver ricaricato la pagina.');
  if(file.path==='restore-source.zip'){
   const sources=await JSZip.loadAsync(bytes);for(const [name,entry] of Object.entries(sources.files))if(!entry.dir)zip.file('ripristino/'+name,await entry.async('uint8array'));
  }else if(file.path==='index.html'){
   const html=new TextDecoder().decode(bytes).replace('<head>','<head><script src="/offline-config.js"></script>');zip.file('offline/index.html',html);
  }else zip.file('offline/'+file.path,bytes);
  if(file.path.startsWith('backup-support/'))zip.file(file.path.slice('backup-support/'.length),bytes);
  onProgress(`Preparazione file ${++index} di ${manifest.files.length}…`);
 }
 const json=JSON.stringify(data,null,2);zip.file('offline/offline-data.json',json);zip.file('ripristino/dati-tutti-gli-anni.json',json);
 zip.file('offline/offline-config.js','window.__PIVA_OFFLINE__=true;');
 zip.file('offline/_headers',"/*\n  Content-Security-Policy: default-src 'self' blob: data:; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'\n");
 for(const [name,entry] of Object.entries(zip.files))if(!entry.dir)hashes[name]=await digest(await entry.async('uint8array'));
 zip.file('MANIFESTO.json',JSON.stringify({format:1,createdAt:data.createdAt,revision,schemaDate:manifest.schemaDate,years:tables.fiscal_years.map(y=>y.fiscal_year),counts:Object.fromEntries(Object.entries(tables).map(([name,rows])=>[name,rows.length])),sha256:hashes},null,2));
 onProgress('Creazione archivio ZIP…');return zip.generateAsync({type:'uint8array',compression:'DEFLATE',compressionOptions:{level:1}});
}
