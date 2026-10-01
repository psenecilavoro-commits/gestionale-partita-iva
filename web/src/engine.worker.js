let runtime;
async function init(){
  const runtimeModule='/runtime/pyodide.mjs';
  const {loadPyodide}=await import(/* @vite-ignore */ runtimeModule);
  runtime=await loadPyodide({indexURL:'/runtime/'});
  const response=await fetch('/engine.json.gz');
  const sources=JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text());
  runtime.FS.mkdir('/app');
  for(const [name,source] of Object.entries(sources)) runtime.FS.writeFile(`/app/${name}`,source);
  runtime.runPython("import sys\nsys.path.insert(0, '/app')\nimport react_bridge\nimport json");
}
self.onmessage=async ({data})=>{
  try {
    if(!runtime) await init();
    runtime.globals.set('request_json',JSON.stringify(data.request));
    const result=runtime.runPython('react_bridge.render(json.loads(request_json))');
    self.postMessage({id:data.id,result:JSON.parse(result)});
  }catch(error){self.postMessage({id:data.id,error:String(error)});}
};
