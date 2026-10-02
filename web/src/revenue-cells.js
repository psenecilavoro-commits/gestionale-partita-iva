const MONTHS=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
export function revenueCell(records,column,index,tables,year){
  const years=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(year));
  if(years.length!==1||records.length!==12||!records.every((r,i)=>r.Mese===MONTHS[i]&&Object.hasOwn(r,'Totale mese')))return null;
  const principals=(tables.principals||[]).filter(p=>p.name===column);
  if(principals.length!==1||['Mese','Totale mese'].includes(column))return null;
  const fy=years[0],principal=principals[0],month=index+1;
  const rows=(tables.monthly_revenues||[]).filter(r=>r.fiscal_year_id===fy.id&&r.principal_id===principal.id&&Number(r.month)===month);
  if(rows.length>1)return null;
  return {year:Number(year),yearId:fy.id,principalId:principal.id,name:column,month,monthName:MONTHS[index],record:rows[0]||null,editable:fy.status==='open'};
}
