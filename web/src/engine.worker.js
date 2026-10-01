let runtime;
let initialization;
let queue=Promise.resolve();
async function init(){
  const runtimeModule='/runtime/pyodide.mjs';
  const {loadPyodide}=await import(/* @vite-ignore */ runtimeModule).catch(error=>{throw Error("Avvio runtime: "+error.message)});
  runtime=await loadPyodide({indexURL:'/runtime/'}).catch(error=>{throw Error('Caricamento runtime: '+error.message)});
  const response=await fetch('/engine.json.gz').catch(error=>{throw Error('Caricamento formule: '+error.message)});
  const sources=JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text());
  runtime.FS.mkdir('/app');
  for(const [name,source] of Object.entries(sources)) runtime.FS.writeFile(`/app/${name}`,source);
  runtime.runPython("import sys\nsys.path.insert(0, '/app')\nimport react_bridge\nimport json");
  for(const wheel of ['pypdf-6.19.0-py3-none-any.whl','defusedxml-0.7.1-py2.py3-none-any.whl']){
    const response=await fetch('/runtime/wheels/'+wheel).catch(error=>{throw Error('Caricamento '+wheel+': '+error.message)});if(!response.ok)throw Error('Lettore documenti non disponibile');
    runtime.FS.writeFile('/app/package.whl',new Uint8Array(await response.arrayBuffer()));
    runtime.runPython("import zipfile\nwith zipfile.ZipFile('/app/package.whl') as wheel: wheel.extractall('/app')");
  }
}
self.onmessage=({data})=>{queue=queue.then(async()=>{
  try {
    if(!initialization)initialization=init().catch(error=>{initialization=null;throw error;});
    await initialization;
    runtime.globals.set('request_json',JSON.stringify(data.request));
    const code=data.request.operation==='clear_session'?'json.dumps(react_bridge.clear_session())':data.request.operation==='inspect_document'?'json.dumps(react_bridge.inspect_document(json.loads(request_json)))':'react_bridge.render(json.loads(request_json))';
    const result=runtime.runPython(code);
    self.postMessage({id:data.id,result:JSON.parse(result)});
  }catch(error){self.postMessage({id:data.id,error:String(error)});}
});};
