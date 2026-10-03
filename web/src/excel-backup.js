import ExcelJS from 'exceljs';

export const BACKUP_PAGES=['Fatturato','Auto','Accantonamenti','Conto economico','Costi','Imposte','Detrazioni e deduzioni','Ammortamenti'];
const money='#,##0.00 "€"';
const blue='23628B';
export function numericValue(value){
  if(typeof value!=='string')return value;
  if(value==='—')return null;
  if(/^-?[\d.]+,\d{2} €$/.test(value))return Number(value.replaceAll('.','').replace(',','.').replace(' €',''));
  return value;
}
function styleSheet(ws){
  ws.views=[{state:'frozen',ySplit:3}];
  ws.properties.defaultRowHeight=20;
  ws.getColumn(1).width=38;
  ws.pageSetup={orientation:'landscape',paperSize:9,fitToPage:true,fitToWidth:1,fitToHeight:0};
}
function heading(ws,label){
  const row=ws.addRow([label]);row.font={bold:true,color:{argb:blue},size:12};row.height=26;
}
function table(ws,records){
  if(!records.length)return;
  const keys=[...new Set(records.flatMap(r=>Object.keys(r)))];
  const header=ws.addRow(keys);header.font={bold:true,color:{argb:'FFFFFFFF'}};header.fill={type:'pattern',pattern:'solid',fgColor:{argb:blue}};
  for(const [index,record] of records.entries()){
    const row=ws.addRow(keys.map(k=>numericValue(record[k])??null));
    row.eachCell(cell=>{cell.font={name:'Calibri',size:11};if(typeof cell.value==='number')cell.numFmt=money;if(index%2===0)cell.fill={type:'pattern',pattern:'solid',fgColor:{argb:'EFF6FC'}};});
  }
  keys.forEach((key,i)=>{ws.getColumn(i+1).width=Math.max(ws.getColumn(i+1).width||0,Math.min(42,Math.max(20,key.length+3)));});
  ws.addRow([]);
}
export function createBackupWorkbook({year,tables,views,exportedAt=new Date()}){
  const fy=(tables.fiscal_years||[]).find(r=>Number(r.fiscal_year)===Number(year));
  if(!fy)throw Error('Anno fiscale non disponibile per il backup.');
  const workbook=new ExcelJS.Workbook();workbook.creator='Gestionale Partita IVA';workbook.created=exportedAt;
  const info=workbook.addWorksheet('Backup');styleSheet(info);
  heading(info,`Gestionale Partita IVA · ${year}`);
  info.addRows([['Regime',Number(year)===2026?'Forfettario':'Ordinario'],['Stato anno',fy.status],['Esportato il',exportedAt.toISOString()],[],['I prospetti riportano valori e risultati al momento del backup.'],['Le formule fiscali sono valutate dal motore del gestionale.'],['I fogli Dati conservano tutte le registrazioni accessibili, anche degli altri anni.'],['Gli importi a zero sono distinti dalle celle non compilate.'],['Il file conserva i dati; il ripristino automatico non è incluso.'],[]]);
  const index=info.addRow(['Foglio dati','Tabella originale','Registrazioni']);index.font={bold:true};
  function visit(ws,nodes){for(const n of nodes||[]){
    if(n.hidden)continue;
    if(['header','subheader'].includes(n.kind))heading(ws,n.label);
    if(n.kind==='metric')ws.addRow([n.label,numericValue(n.value)]).getCell(2).numFmt=money;
    if(n.kind==='table'&&Array.isArray(n.records))table(ws,n.records);
    if(['info','warning','error','caption'].includes(n.kind)&&n.label){const row=ws.addRow([n.label]);ws.mergeCells(row.number,1,row.number,5);row.getCell(1).alignment={wrapText:true,vertical:'top'};row.height=Math.max(30,Math.ceil(n.label.length/100)*16+10);}
    visit(ws,n.children);
  }}
  for(const name of BACKUP_PAGES){
    if(!views[name]?.tree||views[name].mutations?.length)throw Error('Prospetto di backup non valido.');
    const ws=workbook.addWorksheet(name);styleSheet(ws);heading(ws,`${name} · ${year}`);ws.addRow([]);visit(ws,views[name].tree);
  }
  let indexNumber=0;
  for(const [name,records] of Object.entries(tables)){
    if(!Array.isArray(records))throw Error('Dati di backup non validi.');
    const sheetName=`Dati ${String(++indexNumber).padStart(2,'0')}`;
    info.addRow([sheetName,name,records.length]);
    const ws=workbook.addWorksheet(sheetName);styleSheet(ws);heading(ws,name);ws.addRow([]);
    const keys=[...new Set(records.flatMap(r=>Object.keys(r)))];ws.addRow(keys);
    for(const r of records)ws.addRow(keys.map(k=>r[k]===null||r[k]===undefined?null:typeof r[k]==='object'?JSON.stringify(r[k]):r[k]));
    keys.forEach((key,i)=>ws.getColumn(i+1).width=Math.min(45,Math.max(20,key.length+2)));
  }
  info.getColumn(1).width=88;info.getColumn(2).width=40;info.getColumn(3).width=20;
  return workbook;
}
export async function backupBytes(request){return createBackupWorkbook(request).xlsx.writeBuffer();}

