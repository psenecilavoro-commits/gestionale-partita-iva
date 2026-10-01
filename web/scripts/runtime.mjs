import {cp,mkdir,readdir} from 'node:fs/promises';
import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {dirname} from 'node:path';
await mkdir('public/runtime',{recursive:true});
for(const name of await readdir('node_modules/pyodide')) {
  if(/\.(mjs|js|wasm|zip|json)$/.test(name)) await cp(`node_modules/pyodide/${name}`,`public/runtime/${name}`);
}
const require=createRequire(import.meta.url);
const tessRoot=dirname(require.resolve('tesseract.js/package.json'));
const tessRequire=createRequire(tessRoot+'/package.json');
await mkdir('public/runtime/ocr/core',{recursive:true});
await cp(tessRoot+'/dist/worker.min.js','public/runtime/ocr/worker.min.js');
const core=dirname(tessRequire.resolve('tesseract.js-core/package.json'));
for(const name of await readdir(core))if(/\.wasm(?:\.js)?$/.test(name))await cp(core+'/'+name,'public/runtime/ocr/core/'+name);
const pdf=dirname(require.resolve('pdfjs-dist/package.json'));
await cp(pdf+'/build/pdf.worker.min.mjs','public/runtime/pdf.worker.min.mjs');
for(const directory of ['cmaps','standard_fonts','wasm'])await cp(pdf+'/'+directory,'public/runtime/pdf/'+directory,{recursive:true});
const assets=JSON.parse(await readFile('scripts/document-assets.json','utf8'));
for(const asset of assets){
 await mkdir(dirname('public/runtime/'+asset.path),{recursive:true});
 let bytes;try{bytes=await readFile('public/runtime/'+asset.path);}catch{}
 if(!bytes||createHash('sha256').update(bytes).digest('hex')!==asset.sha256){const r=await fetch(asset.url);if(!r.ok)throw Error('Document asset download failed');bytes=Buffer.from(await r.arrayBuffer());}
 if(createHash('sha256').update(bytes).digest('hex')!==asset.sha256)throw Error('Document asset checksum mismatch');
 await writeFile('public/runtime/'+asset.path,bytes);
}
