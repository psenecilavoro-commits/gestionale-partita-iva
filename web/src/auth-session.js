// Identity is used only to preserve UI state, never to authorize data access.
export function sessionIdentity(session){
  try{
    const payload=session.access_token.split('.')[1];
    const claims=JSON.parse(atob(payload.replace(/-/g,'+').replace(/_/g,'/')));
    if(!session.user?.id||typeof claims.session_id!=='string'||!claims.session_id)return null;
    return JSON.stringify([session.user.id,claims.session_id]);
  }catch{return null;}
}

export function watchSession(auth,onChange){
  let identity=null,active=false,revision=0,disposed=false;
  function receive(event,session){
    if(disposed)return;
    if(event!=='INITIAL_SESSION')revision++;
    const next=sessionIdentity(session);
    if(session&&active&&next&&next===identity&&
      ['INITIAL_SESSION','SIGNED_IN','TOKEN_REFRESHED','USER_UPDATED'].includes(event))return;
    if(!session&&!active)return;
    identity=next;active=!!session;
    onChange(session);
  }
  const {data}=auth.onAuthStateChange(receive);
  // Retain the server validation at startup. A late response must never restore
  // an old login or erase a newer session; transient network failures aren't logout.
  const ticket=revision;
  auth.getUser().then(({data,error})=>{
    if(disposed||revision!==ticket)return;
    if(!data?.user&&(!error||error.status===401||error.status===403||error.name==='AuthSessionMissingError'))receive('SIGNED_OUT',null);
  }).catch(()=>{});
  return()=>{disposed=true;data.subscription.unsubscribe();};
}
