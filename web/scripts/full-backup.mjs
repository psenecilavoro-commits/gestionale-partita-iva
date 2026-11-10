import {readFile,writeFile,readdir,stat} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import JSZip from 'jszip';
const revision=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const zip=new JSZip();
const paths=execFileSync('git',['ls-files','-z'],{cwd:'..',encoding:'utf8'}).split('\0').filter(Boolean);
for(const name of paths){
 if(!(/^[^/]+\.py$/.test(name)||/^requirements[^/]*\.txt$/.test(name)||/^web\/(src|engine|scripts)\//.test(name)||/^web\/(package\.json|pnpm-lock\.yaml|vite\.config\.js|index\.html)$/.test(name)||/^web\/public\/(schema\.json|engine\.json\.gz|demo\.json|_headers|_redirects)$/.test(name)||/^web\/public\/backup-support\//.test(name)||name==='migration/build_engine.py'))continue;
 if(/(^|\/)(\.env(?:\.|$)|secrets\.toml$|\.git\/|node_modules\/|\.venv\/)/i.test(name)||/\.(png|jpg|xlsx|csv|pdf)$/i.test(name))continue;
 zip.file('sorgenti/'+name,await readFile('../'+name));
}
const recoverySchema=await readFile('../migration/recovery-schema.sql','utf8');
const pendingReceiptsMigration=await readFile('../migration/invoice-pending-receipts.sql','utf8');
zip.file('sorgenti/migration/recovery-schema.sql',recoverySchema+'\n'+pendingReceiptsMigration);
await writeFile('dist/restore-source.zip',await zip.generateAsync({type:'nodebuffer',compression:'DEFLATE'}));
const files=[];
async function walk(dir){for(const name of await readdir('dist/'+dir)){const path=dir+name,s=await stat('dist/'+path);if(s.isDirectory())await walk(path+'/');else if(!['backup-manifest.json','_headers','_redirects'].includes(path)){const bytes=await readFile('dist/'+path);files.push({path,size:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')});}}}
await walk('');
await writeFile('dist/backup-manifest.json',JSON.stringify({format:1,revision,schemaDate:'2026-10-23',files}));
console.log('Backup completo: '+files.length+' file locali, versione '+revision.slice(0,8));
