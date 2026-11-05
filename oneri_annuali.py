"""Annual credit and deduction ledgers, linked to source records without copies."""
import json
from datetime import date
from decimal import Decimal as D
import streamlit as st
from registri import leggi_tutti, anno_aperto
import detrazioni_deduzioni as dd
from contributi_versati import e_contributo
from ammortamenti import calcola_bene
from sanitarie_documenti import DESCRIZIONE as SANITARIE_DOCUMENTI

PREFIX = 'ONERI_V2|'
CATEGORIE = ['Spese sanitarie','Mutuo','Donazioni','Casa','Mobili','Risparmio energetico',
             'Rec. patrimonio edilizio','Infissi','Condominio','Altra detrazione']
DEDUZIONI = ['Fondo pensione','Donazione deducibile','Altra deduzione']

def metadati(r):
    note = str(r.get('notes') or '')
    if note.startswith(PREFIX):
        try:
            data = json.loads(note[len(PREFIX):])
            if isinstance(data, dict): return data
        except (ValueError, TypeError): pass
    return {}

def categoria(r):
    m = metadati(r)
    if m.get('categoria'): return m['categoria']
    if str(r.get('notes') or '').startswith('TIPO_SANITARIE_FOGLIO') or r['description'] == SANITARIE_DOCUMENTI:
        return 'Spese sanitarie'
    if 'pensione' in r['description'].lower(): return 'Fondo pensione'
    return r['description']

def calcola_detrazioni(crediti, anno):
    righe, sanitario = [], D('0')
    for r in sorted(crediti, key=lambda r:(int(metadati(r).get('riga_excel',999)), categoria(r), int(r['first_fiscal_year']), r['description'])):
        rate, primo = int(r['installment_count']), int(r['first_fiscal_year'])
        rata = dd._numero_rata(anno, primo, rate)
        if rata is None: continue
        m, cat = metadati(r), categoria(r)
        importo, aliquota = D(str(r['original_amount'])), D(str(r['credit_rate']))
        ammesso = D(str(m.get('importo_ammesso', importo)))
        if ammesso < 0 or ammesso > importo: raise ValueError('Importo ammesso non valido: '+r['description'])
        if cat == 'Spese sanitarie':
            if rate != 1 or aliquota != D('.19'):
                raise ValueError('Le spese sanitarie richiedono una rata e aliquota 19%: '+r['description'])
            sanitario += ammesso
            continue
        if cat == 'Mutuo': ammesso = min(ammesso, D('4000'))
        annuo = dd._annuale(ammesso, rate, aliquota, False)
        righe.append({'Categoria':cat,'Causale':r['description'],'Importo':importo,'Importo ammesso':ammesso,'Rate':rate,
            'Anno spesa':int(m.get('anno_spesa', primo)), 'N. rata':rata,
            '% detrazione':aliquota*100,'Importo annuo':annuo})
    if sanitario:
        righe.insert(0, {'Categoria':'Spese sanitarie','Causale':'Spese sanitarie · totale anno',
            'Importo':sanitario,'Importo ammesso':max(sanitario-dd.FRANCHIGIA_FOGLIO,D('0')),'Rate':1,'Anno spesa':anno,'N. rata':1,'% detrazione':D('19'),
            'Importo annuo':dd._annuale(sanitario,1,D('.19'),True)})
    return righe, sum((r['Importo annuo'] for r in righe),D('0'))

def calcola_personali(deduzioni, pensioni):
    righe, fondo, altre = [], D('0'), D('0')
    esplicito = any(not e_contributo(r) and categoria(r)=='Fondo pensione' for r in deduzioni)
    for r in deduzioni:
        if e_contributo(r): continue
        importo = D(str(r['amount']))
        quota = min(importo,D(str(r['deductible_limit']))) if r.get('deductible_limit') is not None else importo
        cat = categoria(r)
        if cat == 'Fondo pensione': fondo += quota
        else: altre += quota
        righe.append({'Categoria':cat,'Causale':r['description'],'Anno':None,
            'Importo':importo,'Quota deducibile':quota,'Origine':metadati(r).get('origine','Inserimento manuale')})
    if not esplicito:
        for r in pensioni:
            valore = D(str(r['amount'])); fondo += valore
            righe.append({'Categoria':'Fondo pensione','Causale':r['description'],'Anno':None,
                'Importo':valore,'Quota deducibile':valore,'Origine':'Versamenti pensione'})
    return righe, fondo, altre

def quote_beni(beni, anno):
    return [{'Categoria':'Ammortamenti','Causale':r['description'],'Anno':anno,
        'Importo':calcola_bene(r,anno)['costo_fiscale'],
        'Quota deducibile':calcola_bene(r,anno)['quota'],
        'Origine':'Ammortamenti · previsto' if r.get('is_planned') else 'Ammortamenti'}
        for r in beni if int(r['first_fiscal_year']) <= anno and calcola_bene(r,anno)['quota'] > 0]

def carica_oneri(client, anno):
    crediti = leggi_tutti(client,'tax_credits')
    deduzioni = leggi_tutti(client,'tax_deductions',fiscal_year_id=anno['id'])
    pensioni = leggi_tutti(client,'pension_payments',fiscal_year_id=anno['id'])
    beni = leggi_tutti(client,'depreciable_assets')
    detrazioni, totale = calcola_detrazioni(crediti,int(anno['fiscal_year']))
    personali, fondo, altre = calcola_personali(deduzioni,pensioni)
    ammortamenti = quote_beni(beni,int(anno['fiscal_year']))
    return dict(crediti=crediti,deduzioni=deduzioni,detrazioni=detrazioni,totale_detrazioni=totale,
        personali=personali,fondo=fondo,altre=altre,ammortamenti=ammortamenti,
        quota_beni=sum((r['Quota deducibile'] for r in ammortamenti),D('0')),
        fondo_presente=any(r['Categoria']=='Fondo pensione' for r in personali))

def _visuale(righe, campi_denaro):
    vista=[]
    for r in righe:
        cat, nome = r.get('Categoria',''), r.get('Causale','')
        causale = cat if not nome else nome if nome==cat or nome.startswith(cat+' · ') else f'{cat} · {nome}'
        v={'Causale':causale}
        for k,valore in r.items():
            if k in ('Categoria','Causale'): continue
            v[k] = (dd._formato(valore) if k in campi_denaro and valore is not None else
                    '—' if valore is None else
                    format(valore.normalize(),'f').replace('.',',')+'%' if k=='% detrazione' else valore)
        vista.append(v)
    return vista

def _nota(cat, **extra): return PREFIX+json.dumps({'categoria':cat,**extra},ensure_ascii=False)

def _salva(client,anno,table,payload,r=None,elimina=False):
    anno_aperto(client,anno)
    if r:
        query=client.table(table).delete() if elimina else client.table(table).update(payload)
        query=query.eq('id',r['id'])
        if table=='tax_deductions': query=query.eq('fiscal_year_id',anno['id'])
    else: query=client.table(table).insert(payload)
    risposta=query.execute()
    if len(risposta.data or [])!=1: raise ValueError('Salvataggio non confermato: aggiorna e verifica la tabella.')
    if not r:
        key=f"oneri_add_{'credit' if table=='tax_credits' else 'deduction'}_{anno['id']}_open"
        st.session_state[key]=False
    st.rerun()

def _form_detrazione(client,anno,record=None):
    r=record or {}; m=metadati(r); anno_num=int(anno['fiscal_year'])
    cat=categoria(r) if r else CATEGORIE[0]
    options=list(dict.fromkeys([*CATEGORIE,cat]))
    with st.form(f"oneri_credit_{r.get('id','new')}_{anno_num}"):
        cat=st.selectbox('Categoria della spesa',options,index=options.index(cat))
        nome=st.text_input('Causale della spesa',value=r.get('description',''))
        importo=st.text_input('Importo della spesa (€)',value=str(r.get('original_amount','')))
        ammesso=st.text_input('Importo ammesso (€; vuoto = intera spesa)',value=str(m.get('importo_ammesso','')))
        spesa=st.number_input('Anno della spesa',min_value=2000,max_value=2100,value=int(m.get('anno_spesa',r.get('first_fiscal_year',anno_num))),step=1)
        prima=st.number_input('Anno della prima rata',min_value=2000,max_value=2100,value=int(r.get('first_fiscal_year',anno_num)),step=1)
        rate=st.number_input('Numero di rate annuali',min_value=1,max_value=30,value=int(r.get('installment_count',1)),step=1)
        percent=st.text_input('Percentuale detrazione (%)',value=str(D(str(r.get('credit_rate','.19')))*100))
        elimina=st.checkbox('Elimina questa detrazione') if r else False
        submit=st.form_submit_button('Salva detrazione')
        annulla=st.form_submit_button('Annulla',key=f"oneri_cancel_credit_{anno['id']}") if not r else False
    if annulla:
        st.session_state[f"oneri_add_credit_{anno['id']}_open"]=False
        st.rerun()
    if submit:
        try:
            nome,valore=dd._validazione_voce(nome or cat,importo)
            base=dd._denaro(ammesso) if ammesso.strip() else valore
            if base>valore: raise ValueError('L’importo ammesso non può superare la spesa.')
            aliquota=dd._aliquota(percent)
            if prima<spesa: raise ValueError('La prima rata non può precedere l’anno della spesa.')
            if cat=='Spese sanitarie' and (int(rate)!=1 or aliquota!=D('.19')): raise ValueError('Per le spese sanitarie indica una rata e il 19%.')
            payload=dict(description=nome,original_amount=str(valore),credit_rate=str(aliquota),
                installment_count=int(rate),first_fiscal_year=int(prima),
                notes=_nota(cat,anno_spesa=int(spesa),importo_ammesso=str(base)))
            _salva(client,anno,'tax_credits',payload,r if r else None,elimina)
        except ValueError as exc: st.warning(str(exc))
        except Exception: st.error('Operazione non confermata: aggiorna e controlla i dati.')

def _form_deduzione(client,anno,record=None):
    r=record or {}; cat=categoria(r) if r else DEDUZIONI[0]
    options=list(dict.fromkeys([*DEDUZIONI,cat]))
    with st.form(f"oneri_deduction_{r.get('id','new')}_{anno['id']}"):
        cat=st.selectbox('Categoria della deduzione',options,index=options.index(cat))
        nome=st.text_input('Causale della deduzione',value=r.get('description',''))
        importo=st.text_input('Importo deducibile dell’anno (€)',value=str(r.get('amount','')))
        giorno=st.text_input('Data del pagamento (AAAA-MM-GG; facoltativa)',value=str(r.get('payment_date') or ''))
        elimina=st.checkbox('Elimina questa deduzione') if r else False
        submit=st.form_submit_button('Salva deduzione')
        annulla=st.form_submit_button('Annulla',key=f"oneri_cancel_deduction_{anno['id']}") if not r else False
    if annulla:
        st.session_state[f"oneri_add_deduction_{anno['id']}_open"]=False
        st.rerun()
    if submit:
        try:
            nome,valore=dd._validazione_voce(nome or cat,importo)
            data=dd._data(giorno,int(anno['fiscal_year'])) if giorno.strip() else None
            payload=dict(description=nome,amount=str(valore),payment_date=data,notes=_nota(cat))
            if not r: payload['fiscal_year_id']=anno['id']
            _salva(client,anno,'tax_deductions',payload,r if r else None,elimina)
        except ValueError as exc: st.warning(str(exc))
        except Exception: st.error('Operazione non confermata: aggiorna e controlla i dati.')

def mostra_oneri(client,anno):
    year=int(anno['fiscal_year'])
    try:
        dati=carica_oneri(client,anno)
        from costi_tabella import dettaglio_annuo_previsionale
        costi=dettaglio_annuo_previsionale(client,anno['id'])
    except Exception as exc:
        st.error('Impossibile leggere i registri: '+str(exc));return
    st.subheader('Detrazioni')
    righe=_visuale(dati['detrazioni'],{'Importo','Importo ammesso','Importo annuo'})
    righe.append({'Causale':'TOTALE','Importo':'','Importo ammesso':'','Rate':'','Anno spesa':'','N. rata':'','% detrazione':'','Importo annuo':dd._formato(dati['totale_detrazioni'])})
    st.dataframe(righe,hide_index=True,width='stretch',height='content')
    st.caption('Le rate pluriennali avanzano automaticamente fino alla scadenza. Le spese a rata singola valgono solo nell’anno indicato e vanno reinserite ogni anno.')
    if anno['status']=='open':
        key=f"oneri_add_credit_{anno['id']}"
        if st.button('Aggiungi spesa detraibile',key=key):st.session_state[key+'_open']=True
        if st.session_state.get(key+'_open'):_form_detrazione(client,anno)
        modificabili=[r for r in dati['crediti'] if r['description']!=SANITARIE_DOCUMENTI and dd._numero_rata(year,int(r['first_fiscal_year']),int(r['installment_count'])) is not None]
        if modificabili:
            with st.expander('Modifica o elimina una detrazione'):
                opzioni={f"{r['description']} · {r['first_fiscal_year']} · {r['id'][:8]}":r for r in modificabili}
                scelta=st.selectbox('Detrazione da modificare',list(opzioni),key=f'oneri_credit_choice_{year}')
                _form_detrazione(client,anno,opzioni[scelta])
        with st.expander('Carica scontrini e ricevute mediche'):
            from sanitarie_unificate import _carica_documenti
            manuali=sum((D(str(r['original_amount'])) for r in dati['crediti'] if categoria(r)=='Spese sanitarie' and r['description']!=SANITARIE_DOCUMENTI and int(r['first_fiscal_year'])==year),D('0'))
            _carica_documenti(client,anno,dati['crediti'],manuali)
    st.divider()
    st.subheader('Deduzioni')
    personali=[{**r,'Anno':year} for r in dati['personali']]
    fonti=[{'Categoria':'Costi','Causale':r['causale'],'Anno':year,'Importo':r['importo'],
        'Quota deducibile':r['deducibile'],'Origine':'Costi · '+r['origine']} for r in costi]
    tutte=[*personali,*fonti,*dati['ammortamenti']]
    tot=sum((r['Quota deducibile'] for r in tutte if r['Quota deducibile'] is not None),D('0'))
    vista=_visuale([{k:v for k,v in r.items() if k!='Origine'} for r in tutte],{'Importo','Quota deducibile'})
    vista.append({'Causale':'TOTALE','Anno':year,'Importo':'','Quota deducibile':'Da completare' if any(r['Quota deducibile'] is None for r in tutte) else dd._formato(tot)})
    st.dataframe(vista,hide_index=True,width='stretch',height='content')
    if anno['status']=='open':
        key=f"oneri_add_deduction_{anno['id']}"
        if st.button('Aggiungi deduzione',key=key):st.session_state[key+'_open']=True
        if st.session_state.get(key+'_open'):_form_deduzione(client,anno)
        modificabili=[r for r in dati['deduzioni'] if not e_contributo(r)]
        if modificabili:
            with st.expander('Modifica o elimina una deduzione'):
                opzioni={f"{r['description']} · {r['id'][:8]}":r for r in modificabili}
                scelta=st.selectbox('Deduzione da modificare',list(opzioni),key=f'oneri_deduction_choice_{year}')
                _form_deduzione(client,anno,opzioni[scelta])
    st.caption('Costi e ammortamenti si aggiornano dalle rispettive schede e dalle fatture importate.')
