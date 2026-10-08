// Document parsing and planning only: no writes, no remote document services.
export const todayISO=()=>new Intl.DateTimeFormat('sv-SE',{timeZone:'Europe/Rome',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function cents(value){
 const text=String(value??'').trim().replace(/€/g,'').replace(/\s/g,'');
 const normalized=text.includes(',')?text.replace(/\./g,'').replace(',','.'):text;
 if(!/^\d{1,12}(?:\.\d{1,2})?$/.test(normalized))throw Error('Importo non valido: usa al massimo due decimali.');
 const [whole,frac='']=normalized.split('.');return BigInt(whole)*100n+BigInt(frac.padEnd(2,'0'));
}
export const money=n=>`${n/100n}.${String(n%100n).padStart(2,'0')}`;
export function validDate(value,today=todayISO()){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(value||'')||new Date(value+'T12:00:00Z').toISOString().slice(0,10)!==value||value>today)throw Error('Controlla le date: devono essere valide e non future.');return value;
}
export function parseInvoiceXML(text,Parser=globalThis.DOMParser){
 if(/<!DOCTYPE|<!ENTITY/i.test(text))throw Error('XML con dichiarazioni esterne non supportato.');
 const doc=new Parser().parseFromString(text,'application/xml');
 const all=(node,name)=>Array.from(node.getElementsByTagName('*')).filter(e=>e.localName===name);
 const first=(node,name)=>all(node,name)[0];
 const val=(node,name)=>first(node,name)?.textContent.trim()||'';
 if(all(doc,'parsererror').length||!first(doc,'FatturaElettronica'))throw Error('Il file non è una fattura elettronica XML valida.');
 const bodies=all(doc,'FatturaElettronicaBody');if(bodies.length!==1)throw Error('Importa una fattura alla volta: questo XML contiene più documenti.');
 const body=bodies[0],general=first(body,'DatiGeneraliDocumento');
 if(val(general,'TipoDocumento')!=='TD01')throw Error('Sono supportate le fatture TD01. Note di credito e documenti speciali richiedono i registri completi.');
 const party=name=>{const node=first(doc,name);return {name:val(node,'Denominazione')||[val(node,'Nome'),val(node,'Cognome')].filter(Boolean).join(' '),taxId:val(node,'IdCodice')||val(node,'CodiceFiscale')};};
 const groups=all(body,'DatiRiepilogo').map(r=>({rate:val(r,'AliquotaIVA'),base:val(r,'ImponibileImporto'),vat:val(r,'Imposta'),nature:val(r,'Natura'),payability:val(r,'EsigibilitaIVA')}));
 if(!groups.length)throw Error('Riepilogo IVA mancante.');
 const total=groups.reduce((n,g)=>n+cents(g.base)+cents(g.vat),0n);
 const declared=val(general,'ImportoTotaleDocumento');
 const special=all(body,'DatiCassaPrevidenziale').length>0||all(body,'ScontoMaggiorazione').length>0||all(body,'DatiBollo').length>0;
 return {source:'XML',number:val(general,'Numero'),invoiceDate:val(general,'Data'),supplier:party('CedentePrestatore'),customer:party('CessionarioCommittente'),groups,total:declared||money(total),description:all(body,'DettaglioLinee').map(r=>val(r,'Descrizione')).join(' · '),lines:all(body,'DettaglioLinee').map(r=>({description:val(r,'Descrizione'),amount:val(r,'PrezzoTotale'),rate:val(r,'AliquotaIVA'),nature:val(r,'Natura')})),special,receivedDate:'',dueDate:val(body,'DataScadenzaPagamento')};
}
export function parseInvoiceText(text){
 const amount='([0-9][0-9.]*,[0-9]{2})';
 const read=label=>new RegExp(label+'\\s*'+amount,'i').exec(text)?.[1]?.replace(/\./g,'').replace(',','.')||'';
 const date=/\b(?:del|data fattura)\s*(\d{2})\/(\d{2})\/(\d{4})/i.exec(text);
 const received=/Data ricezione:\s*(\d{2})\/(\d{2})\/(\d{4})/i.exec(text);
 const total=read('Totale documento'),vat=read('Totale IVA'),base=read('Totale imponibile'),excluded=read('Totale escluso IVA(?:\\s*\\(N1\\))?');
 const groups=[];
 if(base&&vat)groups.push({rate:'22',base,vat,nature:'',payability:'I'});
 if(excluded&&cents(excluded)>0n)groups.push({rate:'0',base:excluded,vat:'0.00',nature:'N1',payability:'I'});
 return {source:'PDF / immagine',number:/\b(?:nr\.|n\.)\s*([^\s]+)/i.exec(text)?.[1]||'',invoiceDate:date?`${date[3]}-${date[2]}-${date[1]}`:'',supplier:{name:'',taxId:''},customer:{name:'',taxId:''},groups,total,description:text.slice(0,2000),lines:[],special:false,receivedDate:received?`${received[3]}-${received[2]}-${received[1]}`:'',dueDate:''};
}
export function suggestCategory(invoice,categories){
 const text=(invoice.description+' '+invoice.supplier.name).toLowerCase();
 const hints=[['rate_auto',/leasing|canone di locazione|volkswagen bank/],['carburante',/carburante|benzina|gasolio/],['autostrada',/autostrada|pedaggio|telepass/],['manutenzione_auto',/officina|manutenzione auto/],['commercialista',/commercialista|consulenza contabile/],['assicurazione',/assicuraz/],['bollo',/bollo auto/],['gestionale',/gestionale/]];
 return categories.find(c=>hints.some(([code,re])=>c.code===code&&re.test(text)))?.id||'';
}
export function planInvoice(invoice,options,tables,today=todayISO()){
 const d=validDate(invoice.invoiceDate,today),payment=validDate(options.paymentDate||d,today);
 const ordinary=Number(d.slice(0,4))!==2026;
 if(!invoice.number.trim()||invoice.number.length>100)throw Error('Inserisci il numero della fattura.');
 if(invoice.special)throw Error('La fattura contiene bollo, cassa previdenziale o sconti: usa i registri completi per questo documento.');
 if(!invoice.groups.length)throw Error('Completa il riepilogo IVA.');
 let base=0n,vat=0n;
 for(const g of invoice.groups){
  const b=cents(g.base),v=cents(g.vat),r=Number(g.rate);
  if(![0,4,5,10,22].includes(r)||['S','D'].includes(g.payability))throw Error('Aliquota o esigibilità speciale: usa i registri completi.');
  if(r===0&&(!/^N[1-7](\.\d)?$/.test(g.nature)||v!==0n))throw Error('Per una voce senza IVA indica la natura corretta.');
  if(r>0&&(g.nature||((b*BigInt(r)+50n)/100n-v>1n)||((b*BigInt(r)+50n)/100n-v< -1n)))throw Error('Imponibile e IVA non coerenti con l’aliquota.');
  base+=b;vat+=v;
 }
 const total=cents(invoice.total);if(total!==base+vat||total<=0n)throw Error('Il totale deve coincidere con imponibili più IVA. Controlla eventuali trattenute o spese particolari.');
 const fy=date=>{const matches=(tables.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(date.slice(0,4)));if(matches.length!==1)throw Error(`Crea prima l’anno fiscale ${date.slice(0,4)} dalle altre schede.`);if(matches[0].status!=='open')throw Error(`L’anno ${date.slice(0,4)} è chiuso: nessuna registrazione consentita.`);return matches[0];};
 const economic=fy(payment),documentYear=fy(d);
 const subject=options.direction==='emessa'?invoice.customer:invoice.supplier;
 if(!subject.name.trim()||subject.name.length>200)throw Error('Completa la denominazione del soggetto.');
 const key=[options.direction,subject.taxId||subject.name.toLowerCase().trim(),invoice.number.toLowerCase().trim(),d].join('|');
 if((tables.invoice_imports||[]).some(r=>r.document_key===key))throw Error('Questa fattura è già stata importata.');
 const payload={direction:options.direction,document_key:key,invoice_number:invoice.number.trim(),invoice_date:d,payment_date:payment,subject:subject.name.trim(),tax_id:subject.taxId||'',total:money(total),base:money(base),vat:money(vat),economic_year_id:economic.id,document_year_id:documentYear.id,groups:invoice.groups.map(g=>({...g,base:money(cents(g.base)),vat:money(cents(g.vat))}))};
 const destinations=[];
 if(options.direction==='emessa'){
  if(ordinary&&invoice.groups.some(g=>Number(g.rate)!==22))throw Error('Per le fatture emesse ordinarie sono supportate le provvigioni con IVA al 22%.');
  if(!ordinary&&vat!==0n)throw Error('Il modello 2026 è forfettario: controlla l’IVA della fattura emessa.');
  if((Number(payment.slice(0,4))===2026)!==(!ordinary))throw Error('Incasso a cavallo del cambio di regime: serve una verifica prima di usare i registri manuali.');
  const principal=(tables.principals||[]).find(p=>p.id===options.principalId);if(!principal)throw Error('Seleziona la mandante.');
  if((tables.sales_vat_invoices||[]).some(r=>r.principal_id===principal.id&&r.invoice_number.toLowerCase().trim()===payload.invoice_number.toLowerCase()&&r.invoice_date===d))throw Error('Fattura già presente nel registro IVA vendite.');
  const monthly=(tables.monthly_revenues||[]).filter(r=>r.fiscal_year_id===economic.id&&r.principal_id===principal.id&&Number(r.month)===Number(payment.slice(5,7)));
  if(monthly.length>1)throw Error('Più registrazioni mensili: controlla prima il Fatturato.');
  payload.principal_id=principal.id;payload.previous_amount=monthly[0]?.amount??null;
  destinations.push(`Fatturato · ${principal.name} · ${payment.slice(0,7)}: ${money(base)} € da aggiungere (totale ${money(cents(monthly[0]?.amount??0)+base)} €)`);
  if(ordinary)destinations.push(`IVA vendite · ${d.slice(0,7)}: ${money(vat)} €`);
 }else if(options.direction==='ricevuta'){
  const asset=options.purchaseKind==='asset';
  const category=(tables.cost_categories||[]).find(c=>c.id===options.categoryId&&c.fiscal_year_id===economic.id);
  if(!asset&&!category)throw Error('Seleziona una categoria configurata per l’anno del pagamento.');
  if(!asset&&['pc','telefono_tablet','penale_km'].includes(category.code))throw Error('Per PC e telefono scegli «Bene da ammortizzare»; per le penali usa il modulo completo.');
  if(!asset)payload.category_id=category.id;
  const auto=asset?options.assetVatCategory==='auto':['rate_auto','carburante','autostrada','manutenzione_auto','assicurazione','bollo'].includes(category.code);
  if(auto&&!asset){const vehicles=tables.vehicles||[];if(vehicles.length!==1)throw Error('Serve una sola auto associata.');payload.vehicle_id=vehicles[0].id;}
  const registered=validDate(options.registeredDate,today),received=validDate(options.receivedDate||d,today);
  if(received<d||registered<received)throw Error('Ricezione e registrazione devono seguire la data fattura.');
  const vatYear=fy(registered);payload.vat_year_id=vatYear.id;payload.received_date=received;payload.registered_date=registered;
  payload.deductible_vat=Number(vatYear.fiscal_year)===2026?'0.00':money(cents(options.deductibleVat));
  if(cents(payload.deductible_vat)>vat)throw Error('L’IVA detraibile non può superare l’IVA indicata.');
  payload.vat_category=auto?'auto':'altro';
  if((tables.purchase_vat_invoices||[]).some(r=>r.supplier.toLowerCase().trim()===subject.name.toLowerCase().trim()&&r.invoice_number.toLowerCase().trim()===payload.invoice_number.toLowerCase()&&r.invoice_date===d))throw Error('Fattura già presente nel registro IVA acquisti.');
  if(asset){
   const purchase=validDate(options.assetPurchaseDate||d,today),assetYear=fy(purchase);
   const description=String(options.assetDescription||'').trim().replace(/\s+/g,' ');
   if(!description||description.length>200)throw Error('Inserisci una descrizione del bene, fino a 200 caratteri.');
   if(!['auto','altro'].includes(options.assetVatCategory))throw Error('Seleziona la categoria IVA del bene.');
   if((Number(assetYear.fiscal_year)===2026)!==(Number(vatYear.fiscal_year)===2026))throw Error('Bene e IVA a cavallo del cambio di regime: usa il modulo completo per la verifica.');
   const fiscalCost=total-cents(payload.deductible_vat);
   let rate='1';
   if(fiscalCost>51646n){
    const percent=String(options.assetRate||'').trim().replace(',','.');
    if(!/^\d{1,3}(?:\.\d{1,4})?$/.test(percent)||Number(percent)<=0||Number(percent)>100)throw Error('Per questo bene inserisci il coefficiente di ammortamento, maggiore di 0 e fino a 100%.');
    rate=(Number(percent)/100).toFixed(6);
   }
   if((tables.depreciable_assets||[]).some(a=>!a.is_planned&&a.purchase_date===purchase&&String(a.description).trim().toLowerCase()===description.toLowerCase()&&cents(a.gross_amount)===total))throw Error('Un bene con questa descrizione, data e importo è già registrato.');
   payload.purchase_kind='asset';payload.asset_year_id=assetYear.id;payload.asset_description=description;payload.asset_purchase_date=purchase;payload.asset_rate=rate;
   destinations.push(`Ammortamenti · ${description} · acquisto ${purchase}: costo fiscale ${money(fiscalCost)} €`);
   destinations.push(fiscalCost<=51646n?'Deduzione integrale secondo il modello esistente.':`Coefficiente ${options.assetRate}% · quote annuali calcolate dalla scheda Ammortamenti.`);
   destinations.push('L’importo non viene aggiunto al registro delle spese ordinarie.');
  }else destinations.push(`Costi${auto?' e Auto':''} · ${category.name} · ${payment.slice(0,7)}: ${money(total)} €`);
  if(Number(vatYear.fiscal_year)!==2026)destinations.push(`IVA acquisti · ${registered.slice(0,7)}: ${payload.deductible_vat} € detraibili`);
 }else throw Error('Scegli fattura emessa o ricevuta.');
 return {payload,destinations,assumedPayment:!options.paymentDate,key};
}
