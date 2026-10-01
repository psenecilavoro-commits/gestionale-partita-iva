// No remote document processing: all bytes stay in this browser session.
async function recognize(canvas){
 const {createWorker}=await import('tesseract.js');
 const worker=await createWorker(['ita','eng'],1,{workerPath:'/runtime/ocr/worker.min.js',corePath:'/runtime/ocr/core',langPath:'/runtime/ocr/lang',workerBlobURL:false,gzip:false,cacheMethod:'none'});
 let timer;
 try{
  await worker.setParameters({tessedit_pageseg_mode:'6'});
  return await Promise.race([worker.recognize(canvas).then(r=>r.data.text),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Lettura OCR oltre il limite di 15 secondi.')),15000);})]);
 }finally{clearTimeout(timer);await worker.terminate();}
}
function normalized(image){
 if(image.width*image.height>18000000)throw Error('Immagine troppo grande: riduci la risoluzione e riprova.');
 const scale=Math.min(1,2400/image.width,2400/image.height);
 const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(image.width*scale));canvas.height=Math.max(1,Math.round(image.height*scale));
 const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(image,0,0,canvas.width,canvas.height);
 const pixels=context.getImageData(0,0,canvas.width,canvas.height);let min=255,max=0;
 for(let i=0;i<pixels.data.length;i+=4){const gray=Math.round(.299*pixels.data[i]+.587*pixels.data[i+1]+.114*pixels.data[i+2]);pixels.data[i]=gray;min=Math.min(min,gray);max=Math.max(max,gray);}
 for(let i=0;i<pixels.data.length;i+=4){const gray=max>min?Math.floor((pixels.data[i]-min)*255/(max-min)):pixels.data[i];pixels.data[i]=pixels.data[i+1]=pixels.data[i+2]=gray;}
 context.putImageData(pixels,0,0);return canvas;
}
export async function prepareDocument(file,base64,inspect,medical){
 const extension=file.name.toLowerCase().split('.').pop();
 if(extension==='xml')return {};
 if(!['pdf','jpg','jpeg','png'].includes(extension))throw Error('Formato documento non supportato.');
 if(extension!=='pdf'){
  const image=await createImageBitmap(file,{imageOrientation:'from-image'});
  try{return {document_text:await recognize(normalized(image))};}finally{image.close();}
 }
 const inspection=await inspect({operation:'inspect_document',base64,medical});
 if(!inspection.needs_ocr)return {document_text:inspection.text};
 const pdfjs=await import('pdfjs-dist/build/pdf.mjs');pdfjs.GlobalWorkerOptions.workerSrc='/runtime/pdf.worker.min.mjs';
 const task=pdfjs.getDocument({data:new Uint8Array(await file.arrayBuffer()),isEvalSupported:false,disableFontFace:true,useSystemFonts:true,cMapUrl:'/runtime/pdf/cmaps/',cMapPacked:true,standardFontDataUrl:'/runtime/pdf/standard_fonts/',wasmUrl:'/runtime/pdf/wasm/'});
 let pdf;
 try{
  pdf=await task.promise;const text=[];
  for(let i=1;i<=pdf.numPages;i++){
   const page=await pdf.getPage(i);const viewport=page.getViewport({scale:2});
   if(viewport.width*viewport.height>18000000)throw Error('Pagina troppo grande.');
   const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
   await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
   text.push(await recognize(normalized(canvas)));canvas.width=canvas.height=0;page.cleanup();
  }
  return {document_text:text.join('\n')||inspection.text};
 }finally{await task.destroy();}
}
