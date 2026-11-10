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

def iva_vendite_ibrida(fatturati, importazioni, documenti, anno_id):
    """Conta l'IVA del documento nel periodo IVA e scorpora solo l'incasso manuale."""
    documenti_per_id = {r["id"]: r for r in documenti}
    imponibili = {}
    iva_documentata = {}
    fatture_viste = set()
    for r in importazioni:
        if r["direction"] != "emessa":
            continue
        anno_incasso = r["economic_year_id"] == anno_id
        anno_iva = r["document_year_id"] == anno_id
        if not (anno_incasso or anno_iva):
            continue
        ids = r["record_ids"]
        fattura = documenti_per_id.get(ids.get("sale"))
        if not fattura or (anno_incasso and not ids.get("revenue")) or fattura["id"] in fatture_viste:
            raise ValueError("Collegamento fattura e incasso non valido.")
        fatture_viste.add(fattura["id"])
        if anno_incasso:
            incasso = ids["revenue"]
            imponibili[incasso] = imponibili.get(incasso, D("0")) + D(str(fattura["taxable_amount"]))
        if anno_iva:
            mese = int(fattura["vat_month"])
            iva_documentata[mese] = iva_documentata.get(mese, D("0")) + D(str(fattura["vat_amount"]))

    manuali = []
    for r in fatturati:
        base_importata = imponibili.pop(r["id"], D("0"))
        if base_importata:
            residuo = D(str(r["amount"])) - base_importata
            if residuo < 0:
                raise ValueError("Incasso inferiore agli imponibili delle fatture collegate.")
            r = {**r, "amount": residuo, "notes": ""}
        manuali.append(r)
    if imponibili:
        raise ValueError("Incasso collegato a una fattura importata non trovato.")

    vendite = iva_vendite_mensile(manuali)
    for mese, iva in iva_documentata.items():
        vendite[mese] = vendite.get(mese, D("0")) + iva
    return vendite


def leggi_iva_vendite_ibrida(client, fatturati, anno_id):
    from registri import leggi_tutti

    importazioni = leggi_tutti(client, "invoice_imports")
    documenti = leggi_tutti(client, "sales_vat_invoices") if importazioni else []
    return iva_vendite_ibrida(fatturati, importazioni, documenti, anno_id)


def calcola_saldi_mensili(fatturati,fatture,anno,*,vendite=None):
    if vendite is None:
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
