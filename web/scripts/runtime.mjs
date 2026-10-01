import {cp,mkdir,readdir} from 'node:fs/promises';
await mkdir('public/runtime',{recursive:true});
for(const name of await readdir('node_modules/pyodide')) {
  if(/\.(mjs|js|wasm|zip|json)$/.test(name)) await cp(`node_modules/pyodide/${name}`,`public/runtime/${name}`);
}
