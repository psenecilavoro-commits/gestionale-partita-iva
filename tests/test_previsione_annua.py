import unittest
from decimal import Decimal as D
from unittest.mock import patch

from accantonamenti_confronto import _obiettivo_ordinario, ripartisci_residuo
from conto_economico import valori_conto_corrente
from costi_tabella import _tabella, totali_annui_previsionali
from imposte_parametri import GRUPPI


class PrevisioneAnnua(unittest.TestCase):
    def fixtures(self, year):
        categories = {
            'commercialista': dict(id='c', name='Commercialista', vat_rate='0.22', vat_deductible_rate='1', cost_deductible_rate='1'),
            'carburante': dict(id='f', name='Carburante', vat_rate='0.22', vat_deductible_rate='1', cost_deductible_rate='0.8'),
        }
        estimates = {'c': dict(category_id='c', estimated_gross_amount='1220', amount_includes_vat=True, notes='INSERIMENTO MANUALE')}
        expenses = [dict(category_id='f', vehicle_id='v', gross_amount=str(amount), expense_date=f'{year}-{month:02}-01', amount_includes_vat=True,
                         vat_rate='0.22', vat_deductible_rate='1', cost_deductible_rate='0.8', notes='INSERIMENTO MANUALE') for month, amount in [(1,122),(2,244)]]
        return categories, estimates, expenses, [], [], []

    def test_total_uses_annual_estimate_and_projects_recorded_months_without_intermediate_rounding(self):
        data = self.fixtures(2027)
        with patch('costi_tabella._leggi', return_value=data):
            totals = totali_annui_previsionali(None,'y')
        self.assertEqual(totals['lordo'],D('3416'))
        self.assertEqual(totals['netto'],D('2800'))
        self.assertEqual(totals['deducibile'],D('2440'))
        rows, incomplete, _ = _tabella(data[0], data[1], data[2], [], [])
        self.assertFalse(incomplete)
        self.assertEqual(rows[-1]['Da dedurre'],'2.440,00 €')

    def test_annual_costs_and_revenue_recalculate_economic_forecast_and_remaining_reserve(self):
        params = {r[0]:dict(value=r[2]) for _,group in GRUPPI for r in group}
        for year in (2027,2030):
            with self.subTest(year=year):
                annual = dict(id='y', fiscal_year=year,status='open')
                data = self.fixtures(year)
                revenues = [dict(principal_id='p',month=1,amount='10000'),dict(principal_id='p',month=2,amount='10000')]
                with patch('costi_tabella._leggi',return_value=data), patch('conto_economico.leggi_parametri',return_value=params), \
                     patch('conto_economico.elenco_mandanti',return_value=[dict(id='p',name='Mandante',enasarco_relationship='plurimandatario')]), \
                     patch('conto_economico.leggi_fatturato',return_value=revenues), patch('accantonamenti_confronto.st.session_state',{}), patch('oneri_annuali.carica_oneri',return_value={'quota_beni':D('0'),'fondo':D('5300'),'totale_detrazioni':D('0'),'altre':D('0')}):
                    first = valori_conto_corrente(None,annual,D('8000'),D('5300'))
                    self.assertEqual(first['B1'],D('120000'))
                    self.assertEqual(first['COSTI_DEDUCIBILI'],D('2440'))
                    goal1,_ = _obiettivo_ordinario(None,annual)
                    quota1 = ripartisci_residuo(goal1,D('5000'),4)['quota_mensile']
                    data[1]['c']['estimated_gross_amount']='2440'
                    second = valori_conto_corrente(None,annual,D('8000'),D('5300'))
                    self.assertEqual(second['COSTI_DEDUCIBILI'],D('3440'))
                    goal2,_ = _obiettivo_ordinario(None,annual)
                    self.assertLess(ripartisci_residuo(goal2,D('5000'),4)['quota_mensile'],quota1)
                    revenues[1]['amount']='20000'
                    third = valori_conto_corrente(None,annual,D('8000'),D('5300'))
                    self.assertEqual(third['B1'],D('180000'))
                    goal3,_ = _obiettivo_ordinario(None,annual)
                    self.assertGreater(goal3,goal2)

    def test_missing_or_unverified_deductions_never_become_zero(self):
        with patch('costi_tabella._leggi',return_value=({}, {}, [], [], [], [])):
            with self.assertRaisesRegex(ValueError,'Inserisci le stime'):
                totali_annui_previsionali(None,'y')
        data = self.fixtures(2027)
        data[0]['rate_auto'] = {**data[0]['carburante'],'id':'r','name':'Rate auto'}
        data[2].append({**data[2][0],'category_id':'r'})
        with patch('costi_tabella._leggi',return_value=data):
            with self.assertRaisesRegex(ValueError,'rate_auto'):
                totali_annui_previsionali(None,'y')


if __name__=='__main__':
    unittest.main()
