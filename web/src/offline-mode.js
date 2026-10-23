export const OFFLINE=typeof window!=='undefined'&&['127.0.0.1','localhost','[::1]'].includes(window.location.hostname)&&window.__PIVA_OFFLINE__===true;
export function requireOnline(offline=OFFLINE){if(offline)throw Error('Copia offline in sola consultazione: nessuna modifica viene salvata.');}
