import defaults from './tax-defaults.json' with {type:'json'};
export function taxCell(records,column,index,tables,year){
 if(column!=='Valore')return null;
 const group=defaults.find(g=>g.length===records.length&&g.every((v,i)=>records[i].Parametro===v[1]));
 const years=(tables.fiscal_years||[]).filter(y=>Number(y.fiscal_year)===Number(year));
 if(!group||years.length!==1||Number(year)===2026)return null;
 const fy=years[0],[code,name,value,unit]=group[index];
 const rows=(tables.fiscal_parameters||[]).filter(r=>r.fiscal_year_id===fy.id&&r.code===code);
 if(rows.length>1)return null;
 const record=rows[0]||null;
 return {kind:'tax',year:Number(year),yearId:fy.id,code,name,unit,record,displayValue:unit==='RATE'?Number((Number(record?.value??value)*100).toFixed(6)):record?.value??value,editable:fy.status==='open'};
}
export function taxValue(raw,unit){
 let text=String(raw??'').trim().replace(/\s/g,'').replace(/%$/,'');
 if(text.includes(','))text=text.replace(/\./g,'').replace(',','.');
 if(!/^\d+(\.\d{1,6})?$/.test(text))throw Error('Inserisci un numero non negativo con al massimo sei decimali.');
 let value=Number(text);if(unit==='RATE')value/=100;
 if(!Number.isFinite(value)||value>(unit==='RATE'?1:999999999999.999999))throw Error('Valore non valido.');
 return value.toFixed(6);
}
export function taxMutation(editor,tables,value){
 const fy=(tables.fiscal_years||[]).find(y=>y.id===editor.yearId);
 if(fy?.status!=='open')throw Error('Anno chiuso: parametri in sola lettura.');
 const rows=(tables.fiscal_parameters||[]).filter(r=>r.fiscal_year_id===editor.yearId&&r.code===editor.code);
 if(rows.length!==(editor.record?1:0)||(editor.record&&(rows[0].id!==editor.record.id||String(rows[0].value)!==String(editor.record.value))))throw Error('Parametro modificato altrove: annulla e riapri la cella.');
 const payload={value,unit:editor.unit,is_provisional:false,source:'Parametro annuale modificato manualmente',source_date:null};
 return editor.record?{table:'fiscal_parameters',operation:'update',payload,filters:[['id',editor.record.id],['fiscal_year_id',editor.yearId],['code',editor.code],['value',editor.record.value]],expected_rows:1}:{table:'fiscal_parameters',operation:'insert',payload:{...payload,fiscal_year_id:editor.yearId,code:editor.code,description:editor.name},filters:[],expected_rows:1,result_ids:[crypto.randomUUID()]};
}
