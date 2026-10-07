const RETRY_DELAYS=[1000,2000,4000];
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));

// Retry only idempotent reads rejected for a future issuance time. Never
// renew/modify the JWT, relax validation, or replay a write operation here.
export async function readWithJwtRetry(read,wait=sleep){
  for(let attempt=0;;attempt++){
    const result=await read();
    if(result.error?.code!=='PGRST303'||result.error.message!=='JWT issued at future')return result;
    if(attempt===RETRY_DELAYS.length)return {...result,error:{...result.error,message:'Il servizio dati non ha ancora riconosciuto la sessione. Attendi qualche secondo e premi «Aggiorna prospetto». Se il problema persiste, riprova più tardi. (JWT issued at future)'}};
    await wait(RETRY_DELAYS[attempt]);
  }
}
