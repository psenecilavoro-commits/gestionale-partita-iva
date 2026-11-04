import {costCell} from './revenue-cells.js';
export const FUEL_CONFIRMATION='Confermo spesa, importi e assenza di registrazioni duplicate';
export const VAT_CONFIRMATION="Confermo gli importi manuali e l'operazione";
export function isCostSummary(records){
 return Array.isArray(records)&&records.length>0&&records.every(r=>Object.hasOwn(r,'Voce')&&Object.hasOwn(r,'Registrato')&&(Object.hasOwn(r,'Totale annuo stimato')||Object.hasOwn(r,'Stima annua / valore file')));
}
export function isCostReadonly(records,column,index,tables,year,readonly=false){
 if(column==='Voce'||!isCostSummary(records))return false;
 return readonly||!costCell(records,column,index,tables,year)?.editable;
}
export function withoutLegacyPurchaseXML(nodes){
 const start=nodes.findIndex(n=>n.kind==='subheader'&&n.label==="Importa una fattura d'acquisto XML");
 if(start<0)return nodes;
 const end=nodes.findIndex((n,i)=>i>start&&(n.kind==='divider'||n.kind==='subheader'));
 return [...nodes.slice(0,nodes[start-1]?.kind==='divider'?start-1:start),...nodes.slice(end<0?nodes.length:end)];
}
// Only explicit submission of these two forms replaces their redundant check.
// Reconciliation, VAT inclusion, deletion and all other confirmations remain.
export function confirmExplicitSubmission(nodes,event,inputs){
 if(!event)return inputs;
 for(const node of nodes||[]){
  const button=node.children?.find(n=>n.kind==='button'&&n.key===event);
  const label=button?.label==='Conferma operazione'?FUEL_CONFIRMATION:button?.label==='Conferma periodo IVA'?VAT_CONFIRMATION:null;
  if(node.kind==='form'&&label){
   const confirmation=node.children.find(n=>n.kind==='checkbox'&&n.label===label);
   if(confirmation)return {...inputs,[confirmation.key]:true};
  }
  const nested=confirmExplicitSubmission(node.children,event,inputs);if(nested!==inputs)return nested;
 }
 return inputs;
}
