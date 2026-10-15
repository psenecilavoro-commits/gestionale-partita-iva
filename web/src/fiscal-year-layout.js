export function fiscalYearLayout(result){
 const tree=result?.tree||[],sidebar=result?.sidebar||[];
 const start=tree.findIndex(n=>n.kind==='subheader'&&n.label==='Anno fiscale');
 if(start<0)return {tree,sidebar};
 let end=tree.findIndex((n,i)=>i>start&&n.kind==='tabs');
 if(end<0)end=tree.length;
 const yearNodes=tree.slice(start+1,end),confirmations={};
 const clean=nodes=>nodes.flatMap(n=>{
  if(n.kind==='checkbox'&&/^(chiusura|riapertura)_anno_conferma_/.test(n.key||'')){confirmations[n.key.split('_')[0]]=n.key;return [];}
  const yearButton=n.kind==='button'&&/^(chiusura|riapertura)_anno_btn_/.test(n.key||'');
  return [{...n,...(yearButton?{disabled:false}:{}),...(n.children?{children:clean(n.children)}:{})}];
 });
 let side=clean(sidebar),placed=false;
 const insert=nodes=>nodes.flatMap(n=>{
  if(n.label==='### Gestione anno fiscale'){placed=true;return [n,...yearNodes];}
  return [{...n,...(n.children?{children:insert(n.children)}:{})}];
 });
 side=insert(side);
 if(!placed)side.push({kind:'markdown',label:'### Gestione anno fiscale',id:'year-management'},...yearNodes);
 return {tree:[...tree.slice(0,start),...tree.slice(end)],sidebar:side,confirmations};
}
