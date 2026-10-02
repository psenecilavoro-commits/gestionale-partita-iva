const MONTHS=['Gennaio','Febbraio','Marzo','Aprile','Maggio','Giugno','Luglio','Agosto','Settembre','Ottobre','Novembre','Dicembre'];
const EXPENSE_CODES={Autostrada:'autostrada','Rate auto':'rate_auto'};

function sameMonth(date,year,month){
  const text=String(date||'');
  return text.slice(0,4)===String(year)&&Number(text.slice(5,7))===month;
}

export function autoCell(records,column,index,tables,year){
  if(!Array.isArray(records)||records.length<12||index<0||index>=12)return null;
  if(!records.slice(0,12).every((row,i)=>row?.Mese===MONTHS[i]))return null;
  if(!['Percorrenza','Autostrada','Rate auto'].includes(column))return null;

  const years=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(year));
  if(years.length!==1)return null;
  const fy=years[0];
  const vehicles=tables?.vehicles||[];
  if(vehicles.length!==1)return {kind:'auto-disabled',name:column,month:index+1,monthName:MONTHS[index],editable:false,reason:'Serve una sola auto associata.'};
  const vehicle=vehicles[0];
  const month=index+1;

  if(column==='Percorrenza'){
    const rows=(tables?.vehicle_monthly||[]).filter(r=>r.fiscal_year_id===fy.id&&r.vehicle_id===vehicle.id&&Number(r.month)===month);
    if(rows.length>1)return {kind:'auto-disabled',name:column,month,monthName:MONTHS[index],editable:false,reason:'Sono presenti più percorrenze nello stesso mese.'};
    return {
      kind:'auto-distance',
      year:Number(year),yearId:fy.id,vehicleId:vehicle.id,name:column,
      month,monthName:MONTHS[index],record:rows[0]||null,editable:fy.status==='open',
    };
  }

  const code=EXPENSE_CODES[column];
  const categories=(tables?.cost_categories||[]).filter(c=>c.fiscal_year_id===fy.id&&c.code===code);
  if(categories.length!==1)return {kind:'auto-disabled',name:column,month,monthName:MONTHS[index],editable:false,reason:'Categoria auto non disponibile.'};
  const category=categories[0];
  const rows=(tables?.costs||[]).filter(r=>
    r.fiscal_year_id===fy.id&&r.vehicle_id===vehicle.id&&r.category_id===category.id&&sameMonth(r.expense_date,year,month)
  );
  if(rows.length>1)return {kind:'auto-disabled',name:column,month,monthName:MONTHS[index],editable:false,reason:'Sono presenti più registrazioni nello stesso mese.'};
  return {
    kind:code==='autostrada'?'auto-toll':'auto-installment',
    code,year:Number(year),yearId:fy.id,vehicleId:vehicle.id,category,name:column,
    month,monthName:MONTHS[index],record:rows[0]||null,editable:fy.status==='open',
  };
}
