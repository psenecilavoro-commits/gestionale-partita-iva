function cents(value){
  const match=/^(\d+)(?:\.(\d{1,2}))?$/.exec(String(value));
  if(!match)throw Error('Importo non valido');
  return BigInt(match[1])*100n+BigInt((match[2]||'').padEnd(2,'0'));
}
export function enasarcoSummary(records,alerts){
  if(!Array.isArray(records)||!records.length||!alerts.length||
    !records.every(r=>['Mandante','Mesi compilati','Fatturato','Media mesi compilati','Stima annua'].every(key=>Object.hasOwn(r,key))))return records;
  const estimates=records.map(row=>{
    try{return cents(String(row['Stima annua']).replace(/[€\s]/g,'').replace(/\./g,'').replace(',','.'));}catch{return null;}
  });
  const totalEstimate=estimates.reduce((sum,value)=>sum+(value??0n),0n);
  return records.map((row,index)=>{
    const matches=alerts.filter(a=>a.name===row.Mandante);
    const status=matches.length===1?matches[0].status:null;
    const estimate=estimates[index];
    const incidence=totalEstimate>0n&&estimate!==null
      ?new Intl.NumberFormat('it-IT',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number((estimate*10000n+totalEstimate/2n)/totalEstimate)/100)+' %':'—';
    return {...row,Enasarco:['stop','reached'].includes(status)?'STOP':['go','empty'].includes(status)?'VAI':'—',Incidenza:incidence};
  });
}
export function enasarcoAlerts(tables,year){
  const years=(tables?.fiscal_years||[]).filter(f=>Number(f.fiscal_year)===Number(year));
  if(years.length!==1)return [];
  const fy=years[0];
  return (tables.principals||[]).map(principal=>{
    const base={name:principal.name};
    const suffix={plurimandatario:'pluri',monomandatario:'mono'}[principal.enasarco_relationship];
    const parameters=(tables.fiscal_parameters||[]).filter(p=>p.fiscal_year_id===fy.id&&p.code===`enasarco_massimale_${suffix}`);
    if(!suffix||parameters.length!==1)return {...base,status:'missing'};
    try{
      const limit=cents(parameters[0].value);
      if(limit<=0n)return {...base,status:'missing'};
      const revenues=(tables.monthly_revenues||[]).filter(r=>r.fiscal_year_id===fy.id&&r.principal_id===principal.id);
      const months=new Set();let total=0n;
      for(const revenue of revenues){
        const month=Number(revenue.month);
        if(!Number.isInteger(month)||month<1||month>12||months.has(month))throw Error('Registrazione ambigua');
        months.add(month);total+=cents(revenue.amount);
      }
      return {...base,total,limit,remaining:total<limit?limit-total:0n,provisional:parameters[0].is_provisional===true,status:!revenues.length?'empty':total>limit?'stop':total===limit?'reached':'go'};
    }catch{return {...base,status:'invalid'};}
  });
}
