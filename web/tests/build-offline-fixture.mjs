// After pnpm build, create a synthetic offline archive for browser QA.
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import JSZip from 'jszip';
import {completeBackup,digest} from '../src/full-backup.js';
const manifest=JSON.parse(await readFile('dist/backup-manifest.json'));
const bytes=await completeBackup({tables:JSON.parse(await readFile('public/demo.json')),user:{id:'demo-owner',email:'demo@example.invalid'},revision:manifest.revision,fetchFile:async path=>{
 try{return new Response(await readFile('dist'+path));}catch{return new Response('',{status:404});}
}});
const root='node_modules/.cache/piva-offline-test',zip=await JSZip.loadAsync(bytes);
const hashes=JSON.parse(await zip.file('MANIFESTO.json').async('string')).sha256;
for(const [name,entry] of Object.entries(zip.files))if(!entry.dir){
 const content=await entry.async('uint8array');
 if(name!=='MANIFESTO.json'&&await digest(content)!==hashes[name])throw Error('Hash '+name);
 await mkdir(root+'/'+name.split('/').slice(0,-1).join('/'),{recursive:true});await writeFile(root+'/'+name,content);
}
console.log('Synthetic offline fixture verified: '+bytes.length+' bytes, '+Object.keys(hashes).length+' files.');
