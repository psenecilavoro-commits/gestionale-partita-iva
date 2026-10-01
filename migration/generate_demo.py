"""Synthetic fixtures only: never export private database records."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from imposte_parametri import GRUPPI
from costi import VOCI_TEST, NOTA_CATEGORIA_TEST
from riepilogo_costi import ANNUE, MENSILI
schema=json.loads((ROOT/'migration/supabase-schema-baseline.json').read_text())
tables={t['name']:[] for t in schema['tables']}
tables.update({'sales_vat_invoices':[], 'vat_periods':[], 'pension_payments':[], 'purchase_cost_links':[]})
from auto import NOTA_VEICOLO_TEST
tables['vehicles']=[{'id':'demo-vehicle','user_id':'demo-owner','label':'Auto dimostrativa','acquisition_cost_gross':'39900','acquisition_date':'2026-01-01','contract_start':'2026-01-01','contract_end':'2029-12-31','notes':NOTA_VEICOLO_TEST}]
principals=[{'id':'demo-principal','user_id':'demo-owner','name':'Mandante dimostrativa','enasarco_relationship':'plurimandatario','active':True}]
tables['principals']=principals
for year in (2026,2027):
    fid=f'demo-year-{year}'
    tables['fiscal_years'].append({'id':fid,'user_id':'demo-owner','fiscal_year':year,'status':'open'})
    p={item[0]:item[2] for _,group in GRUPPI for item in group}
    if year==2026:
        p.update({'forfettario_coeff_redditivita':'0.62','forfettario_aliquota_sostitutiva':'0.15','forfettario_limite_ragguagliato':'82205','forfettario_limite_uscita_immediata':'100000','forfettario_mesi_proiezione':'11','forfettario_contributi_ap':'0','forfettario_riduzione_inps':'0.35','inps_fisso_foglio':'3031.76','inps_minimale_foglio':'18808.01','inps_soglia_seconda_foglio':'56224'})
    tables['fiscal_parameters'] += [{'id':f'{fid}-p-{code}','user_id':'demo-owner','fiscal_year_id':fid,'code':code,'value':value,'description':code,'unit':'numero','source':'DATI SINTETICI DI COLLAUDO','is_provisional':True} for code,value in p.items()]
    for month in range(1,9):
        tables['monthly_revenues'].append({'id':f'{fid}-r-{month}','user_id':'demo-owner','fiscal_year_id':fid,'principal_id':'demo-principal','month':month,'amount':'4500.00','notes':'DATI SINTETICI DI COLLAUDO'})
        tables['monthly_reserves'].append({'id':f'{fid}-a-{month}','user_id':'demo-owner','fiscal_year_id':fid,'month':month,'reserved_amount':'600.00','notes':'DATI SINTETICI DI COLLAUDO'})
        tables['monthly_net_commissions'].append({'id':f'{fid}-n-{month}','fiscal_year_id':fid,'month':month,'amount':'3900.00'})
    for item in VOCI_TEST:
        code=item['code'];cid=f'{fid}-cat-{code}'
        tables['cost_categories'].append({'id':cid,'user_id':'demo-owner','fiscal_year_id':fid,'code':code,'name':item['name'],'vat_rate':item['vat_rate'],'vat_deductible_rate':item['vat_deductible_rate'],'cost_deductible_rate':item['cost_deductible_rate'],'deductible_limit':None,'active':True,'notes':NOTA_CATEGORIA_TEST})
        tables['annual_cost_estimates'].append({'id':f'{cid}-estimate','user_id':'demo-owner','fiscal_year_id':fid,'category_id':cid,'estimated_gross_amount':item['gross'],'amount_includes_vat':True,'notes':item['notes']})
    for code,note in MENSILI.items():
        cid=f'{fid}-cat-{code}'
        tables['cost_categories'].append({'id':cid,'user_id':'demo-owner','fiscal_year_id':fid,'code':code,'name':code.replace('_',' ').title(),'vat_rate':'0.22','vat_deductible_rate':'1','cost_deductible_rate':'0.8','deductible_limit':None,'active':True,'notes':NOTA_CATEGORIA_TEST})
        tables['costs'].append({'id':f'{cid}-cost','user_id':'demo-owner','fiscal_year_id':fid,'category_id':cid,'vehicle_id':'demo-vehicle','expense_date':f'{year}-01-01','payment_date':None,'description':'DATI SINTETICI DI COLLAUDO','gross_amount':'100.00','amount_includes_vat':True,'vat_rate':'0.22','vat_deductible_rate':'1','cost_deductible_rate':'0.8','deductible_limit':None,'fiscal_competence_year':year,'notes':note})
    tables['vehicle_year_settings'].append({'id':f'{fid}-car-settings','user_id':'demo-owner','fiscal_year_id':fid,'vehicle_id':'demo-vehicle','annual_km_limit':30000,'excess_km_penalty':'0.10','fiscal_cost_limit':'25822.84','notes':'DATI SINTETICI DI COLLAUDO'})
(ROOT/'web/public/demo.json').write_text(json.dumps(tables,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'web/public/schema.json').write_text(json.dumps({'tables':schema['tables']}),encoding='utf-8')
print('Synthetic demo generated; production database was not accessed')
