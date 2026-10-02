const MONTHS=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
export const RESERVE_LABELS={'Provvigioni nette · manuale':'Provvigioni nette','Accantonato · manuale':'Accantonato','Provv. nette − accantonato · prima IVA':'Provvigioni nette - accantonato'};
export function reserveCell(records,column,index,tables,year){
 if(records.length!==12||!records.every((r,i)=>r.Mese===MONTHS[i]&&Object.hasOwn(r,'Accantonato · manuale')&&Object.hasOwn(r,'Provvigioni nette · manuale')))return null;
 const type=column==='Accantonato · manuale'?['monthly_reserves','reserved_amount','Accantonato']:column==='Provvigioni nette · manuale'?['monthly_net_commissions','amount','Provvigioni nette']:null;
 if(!type)return null;
 const years=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(year));
 if(years.length!==1||!Array.isArray(tables[type[0]]))return null;
 const fy=years[0],month=index+1,rows=tables[type[0]].filter(r=>r.fiscal_year_id===fy.id&&Number(r.month)===month);
 if(rows.length>1)return null;
 return {kind:'reserve',table:type[0],field:type[1],name:type[2],year:Number(year),yearId:fy.id,month,monthName:MONTHS[index],record:rows[0]||null,editable:fy.status==='open'};
}
export function reserveMutation(cell,tables,value){
 if(!(tables.fiscal_years||[]).some(f=>f.id===cell.yearId&&f.status==='open'))throw Error('Anno chiuso: importi in sola lettura.');
 const rows=(tables[cell.table]||[]).filter(r=>r.fiscal_year_id===cell.yearId&&Number(r.month)===cell.month);
 if(rows.length!==(cell.record?1:0)||(cell.record&&(rows[0].id!==cell.record.id||String(rows[0][cell.field])!==String(cell.record[cell.field]))))throw Error('Importo modificato altrove: annulla e riapri la cella.');
 return cell.record?{table:cell.table,operation:'update',payload:{[cell.field]:value},filters:[['id',cell.record.id],['fiscal_year_id',cell.yearId],['month',cell.month],[cell.field,cell.record[cell.field]]],expected_rows:1}:{table:cell.table,operation:'insert',payload:{fiscal_year_id:cell.yearId,month:cell.month,[cell.field]:value},filters:[],expected_rows:1};
}

