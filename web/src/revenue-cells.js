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

export function costCell(records,column,index,tables,year){
  if(Number(year)!==2026)return ordinaryCostCell(records,column,index,tables,year);
  if(Number(year)!==2026||column!=='Stima annua / valore file'||!records.every(r=>Object.hasOwn(r,'Voce')&&Object.hasOwn(r,'Registrato')&&Object.hasOwn(r,column)))return null;
  const name=records[index]?.Voce;
  if(['Auto · rate','Auto - rate','Autostrada','Carburante'].includes(name))return null;
  const years=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===2026);
  if(years.length!==1)return null;
  const fy=years[0],cats=(tables.cost_categories||[]).filter(c=>c.fiscal_year_id===fy.id&&c.name===name);
  if(cats.length!==1)return null;
  const rows=(tables.annual_cost_estimates||[]).filter(r=>r.fiscal_year_id===fy.id&&r.category_id===cats[0].id);
  if(rows.length!==1)return null;
  return {kind:'cost',year:2026,yearId:fy.id,name,record:rows[0],editable:fy.status==='open'};
}

// Order matches costi_scheda.voci_modificabili; calculated and Auto rows are excluded.
const ANNUAL_COSTS=[['bollo','Bollo'],['assicurazione','Assicurazione'],['manutenzione_auto','Manutenzione auto'],['commercialista','Commercialista'],['vitto_alloggio','Vitto e alloggio'],['pc','PC'],['telefono_tablet','Telefono o tablet']];
function ordinaryCostCell(records,column,index,tables,year){
  if(column!=='Totale annuo stimato'||!records.every(r=>Object.hasOwn(r,'Voce')&&Object.hasOwn(r,'Registrato')&&Object.hasOwn(r,'Da dedurre')))return null;
  const years=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(year));
  if(years.length!==1)return null;
  const fy=years[0],categories=(tables.cost_categories||[]).filter(c=>c.fiscal_year_id===fy.id);
  const candidates=ANNUAL_COSTS.filter(([code,name])=>records[index]?.Voce===(categories.find(c=>c.code===code)?.name||name));
  if(candidates.length!==1)return null;
  const [code,name]=candidates[0],cats=categories.filter(c=>c.code===code);
  if(cats.length>1)return null;
  const rows=(tables.annual_cost_estimates||[]).filter(r=>r.fiscal_year_id===fy.id&&r.category_id===cats[0]?.id);
  if(rows.length>1)return null;
  const existing=ANNUAL_COSTS.filter(([key])=>categories.some(c=>c.code===key&&(tables.annual_cost_estimates||[]).some(r=>r.fiscal_year_id===fy.id&&r.category_id===c.id)));
  return {kind:'cost',ordinary:true,code,selection:existing.findIndex(([key])=>key===code),year:Number(year),yearId:fy.id,name:cats[0]?.name||name,record:rows[0]||null,editable:fy.status==='open'};
}