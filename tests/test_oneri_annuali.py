import unittest
from decimal import Decimal as D
from unittest.mock import patch
from oneri_annuali import calcola_detrazioni,calcola_personali,quote_beni,_nota
from costi_tabella import _tabella
from detrazioni_deduzioni import PROVE

class Oneri(unittest.TestCase):
 def test_excel_recalculated_and_installments_expire(self):
  credits=[dict(description=n,original_amount=v,installment_count=rate,credit_rate=tax,first_fiscal_year=2027-num+1 if num else 2027,notes=_nota(n)) for n,v,rate,num,tax,_ in PROVE]
  rows,total=calcola_detrazioni(credits,2027)
  self.assertEqual(total.quantize(D('.01')),D('2941.51'))
  casa=next(r for r in rows if r['Causale']=='Casa' and r['Importo']==D('5321'))
  self.assertEqual(casa['N. rata'],10);self.assertEqual(casa['Importo annuo'],D('266.05'))
  rows28,_=calcola_detrazioni(credits,2028)
  self.assertFalse(any(r['Importo']==D('5321') for r in rows28))
  self.assertFalse(any(r['Categoria']=='Spese sanitarie' for r in rows28))
  self.assertEqual(next(r for r in rows28 if r['Importo']==D('25815'))['N. rata'],10)
 def test_installments_follow_calendar_not_page_visits_and_single_year_never_repeats(self):
  single=dict(description='Mutuo',original_amount='500',credit_rate='.19',installment_count=1,first_fiscal_year=2030,notes=_nota('Mutuo'))
  multiple=dict(description='Casa',original_amount='10000',credit_rate='.5',installment_count=3,first_fiscal_year=2030,notes=_nota('Casa'))
  records=[single,multiple]
  for year,expected in [(2029,[]),(2030,[('Casa',1),('Mutuo',1)]),(2032,[('Casa',3)]),(2033,[])]:
   rows,_=calcola_detrazioni(records,year)
   self.assertEqual(sorted((r['Causale'],r['N. rata']) for r in rows),expected)
  self.assertEqual(len(records),2)
  self.assertEqual(multiple['first_fiscal_year'],2030)
  rows,_=calcola_detrazioni(records,2031)
  self.assertEqual(rows[0]['N. rata'],2)

 def test_health_deductible_threshold_once_across_sources(self):
  base=dict(installment_count=1,first_fiscal_year=2030,credit_rate='.19')
  records=[dict(base,description='Visita',original_amount='100',notes=_nota('Spese sanitarie')),dict(base,description='Spese sanitarie · documenti caricati',original_amount='200',notes='')]
  rows,total=calcola_detrazioni(records,2030)
  self.assertEqual(len(rows),1);self.assertEqual(total,(D('300')-D('129.11'))*D('.19'))
 def test_pension_authoritative_amount_no_double_count_and_contributions_excluded(self):
  deductions=[dict(description='Fondo pensione',amount='5300',notes=_nota('Fondo pensione')),dict(description='INPS',amount='100',notes='CONTRIBUTI_VERSATI_V1|INPS|2027'),dict(description='Altra',amount='200',deductible_limit='150',notes=_nota('Altra deduzione'))]
  rows,fondo,altre=calcola_personali(deductions,[dict(description='Pensione',amount='5300')])
  self.assertEqual(len(rows),2);self.assertEqual(fondo,D('5300'));self.assertEqual(altre,D('150'))
 def test_assets_include_annual_forecast_only_once_not_full_purchase(self):
  asset=dict(description='PC',gross_amount='1220',deductible_vat='220',first_fiscal_year=2027,depreciation_rate='.2',is_planned=False)
  self.assertEqual(quote_beni([asset],2027)[0]['Quota deducibile'],D('100'))
  self.assertEqual(quote_beni([asset],2028)[0]['Quota deducibile'],D('200'))
  self.assertEqual(quote_beni([asset],2026),[])
 def test_imported_annual_expense_uses_existing_cost_source_estimate_overrides_not_adds(self):
  cat=dict(id='c',name='Commercialista',vat_rate='.22',vat_deductible_rate='1',cost_deductible_rate='1',deductible_limit=None)
  cost=dict(cat,category_id='c',gross_amount='1220',amount_includes_vat=True,notes='Importata')
  out={};rows=[]
  _tabella({'commercialista':cat},{},[cost],[],[],totali_output=out,dettaglio_output=rows)
  self.assertEqual(out['deducibile'],D('1000'))
  out={};_tabella({'commercialista':cat},{'c':dict(estimated_gross_amount='2440',amount_includes_vat=True)},[cost],[],[],totali_output=out)
  self.assertEqual(out['deducibile'],D('2000'))

if __name__=='__main__':unittest.main()
