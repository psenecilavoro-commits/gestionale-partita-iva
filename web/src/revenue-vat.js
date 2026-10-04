const MARKER='\n[PIVA_GROSS_22_V1]';
function cents(raw){
 let text=String(raw??'').trim().replace(/\s/g,'');
 if(text.includes(','))text=text.replace(/\./g,'').replace(',','.');
 if(!/^\d+(?:\.\d{1,2})?$/.test(text))throw Error('Inserisci un importo non negativo con al massimo due decimali.');
 const [whole,fraction='']=text.split('.');
 const result=BigInt(whole)*100n+BigInt(fraction.padEnd(2,'0'));
 if(result>99999999999999n)throw Error('Importo troppo elevato.');
 return result;
}
const fixed=n=>`${n/100n}.${String(n%100n).padStart(2,'0')}`;
export function splitGross(raw){
 const gross=cents(raw),net=(gross*100n+61n)/122n;
 return {gross:fixed(gross),net:fixed(net),vat:fixed(gross-net)};
}
export function grossForRecord(record){
 if(!record)return '';
 const amount=cents(record.amount),notes=String(record.notes||'');
 if(notes.includes(MARKER)){
  try{const gross=notes.slice(notes.lastIndexOf(MARKER)+MARKER.length);if(cents(splitGross(gross).net)===amount)return splitGross(gross).gross;}catch{}
 }
 return fixed((amount*122n+50n)/100n);
}