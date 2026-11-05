"""Monthly VAT reserve from recorded turnover and deductible purchase VAT."""
from decimal import Decimal as D, ROUND_HALF_UP
from iva_acquisti import riepilogo_acquisti_iva

CENT=D('.01')
MARKER='\n[PIVA_GROSS_22_V1]'

def iva_vendite_mensile(fatturati):
    risultato={}
    for r in fatturati:
        mese=int(r['month']);netto=D(str(r['amount']))
        if not 1<=mese<=12 or not netto.is_finite() or netto<0:
            raise ValueError('Fatturato mensile non valido.')
        iva=(netto*D('.22')).quantize(CENT,rounding=ROUND_HALF_UP)
        note=str(r.get('notes') or '')
        if MARKER in note:
            try:
                lordo=D(note.rsplit(MARKER,1)[1])
                if lordo.is_finite() and lordo>=0 and (lordo/D('1.22')).quantize(CENT,rounding=ROUND_HALF_UP)==netto:
                    iva=lordo-netto
            except Exception: pass
        risultato[mese]=risultato.get(mese,D('0'))+iva
    return risultato

def calcola_saldi_mensili(fatturati,fatture,anno):
    vendite=iva_vendite_mensile(fatturati)
    acquisti=riepilogo_acquisti_iva(fatture,anno)
    risultato={};credito=D('0')
    for mese in range(1,13):
        gruppo=acquisti.get(mese,{})
        detraibile=gruppo.get('auto',D('0'))+gruppo.get('altro',D('0'))
        emessa=vendite.get(mese)
        if emessa is None:
            # Do not guess how much existing credit an unrecorded month consumed.
            if credito is None or credito>0 or detraibile>0:credito=None
            risultato[mese]={'vendite':None,'detraibile':detraibile,'debito':None,'credito':credito}
            continue
        if credito is None:
            risultato[mese]={'vendite':emessa,'detraibile':detraibile,'debito':None,'credito':None}
            continue
        saldo=emessa-detraibile-credito
        debito=max(saldo,D('0'))
        credito=max(-saldo,D('0'))
        risultato[mese]={'vendite':emessa,'detraibile':detraibile,'debito':debito,'credito':credito}
    return risultato
