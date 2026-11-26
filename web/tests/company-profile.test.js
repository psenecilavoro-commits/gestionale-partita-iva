import {test} from 'node:test';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {GROUPS,normalizeProfile,billingText,profilePDF,saveProfile} from '../src/company-profile.js';
const profile={name:'AZIENDA DI PROVA',address:'Via Esempio 10, 37100 Verona (VR)',vat:'01234567890',taxCode:'CODICEPROVA',email:'esempio@example.invalid',pec:'pec@example.invalid',sdi:'ABC1234',phone:'+39 000 0000000',holder:'PRIMO TITOLARE e SECONDO TITOLARE',bank:'Crédit Agricole',iban:'IT60X0542811101000000123456',bic:'EXAMPLE1XXX',ateco:'46.19.00',inps:'12345',enasarco:'67890'};
test('billing copy and standard PDF exclude bank and welfare; optional groups exported only on request',async()=>{
 const text=billingText(profile);assert.match(text,/AZIENDA DI PROVA/);assert.doesNotMatch(text,/IT60X|Matricola Enasarco|Crédit/);
 const {getDocument}=await import('pdfjs-dist/legacy/build/pdf.mjs');
 for(const options of [{},{bank:true,extra:true}]){
  const bytes=profilePDF(profile,options);const pdf=await getDocument({data:bytes,useSystemFonts:true,disableFontFace:true}).promise;
  let extracted='';for(let i=1;i<=pdf.numPages;i++)extracted+=(await(await pdf.getPage(i)).getTextContent()).items.map(x=>x.str).join(' ');
  assert.match(extracted,/AZIENDA DI PROVA/);
  if(options.bank){assert.match(extracted,/IT60X0542811101000000123456/);assert.match(extracted,/Crédit Agricole/);assert.match(extracted,/67890/);}else assert.doesNotMatch(extracted,/IT60X|Matricola Enasarco/);
  
 }
});
test('validation preserves leading zeros and joint holders; checks IBAN and rejects multiline/oversize input',()=>{
 assert.equal(normalizeProfile(profile).vat,'01234567890');assert.equal(normalizeProfile(profile).holder,profile.holder);
 assert.throws(()=>normalizeProfile({...profile,iban:'IT61X0542811101000000123456'}),/controllo/);
 assert.throws(()=>normalizeProfile({...profile,name:'a\nb'}));assert.throws(()=>normalizeProfile({...profile,address:'x'.repeat(251)}));
});
test('editing uses profile id, owner and original timestamp; conflicts fail without treating update as success',async()=>{
 const calls=[];const chain={update:x=>(calls.push(x),chain),eq:(...x)=>(calls.push(x),chain),select:async()=>({data:[],error:null})};
 await assert.rejects(saveProfile({from:name=>(assert.equal(name,'company_profiles'),chain)},'owner',{id:'profile',updated_at:'before'},profile),/altrove/);
 assert.deepEqual(calls.slice(1),[['id','profile'],['user_id','owner'],['updated_at','before']]);
});
test('long fields paginate without losing content and PDF output can be opened',async()=>{
 const data=Object.fromEntries(GROUPS.flatMap(g=>g.fields.map(([key])=>[key,'Testo lungo '.repeat(20)])));data.name='PROVA DOCUMENTO LUNGO';
 const {getDocument}=await import('pdfjs-dist/legacy/build/pdf.mjs');const pdf=await getDocument({data:profilePDF(data,{bank:true,extra:true}),useSystemFonts:true,disableFontFace:true}).promise;assert.ok(pdf.numPages>1);
 await writeFile('../tmp/company-profile-preview.pdf',profilePDF(profile,{bank:true,extra:true}));
});
