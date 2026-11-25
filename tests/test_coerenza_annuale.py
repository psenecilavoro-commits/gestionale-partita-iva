"""Annual projections must converge and share fiscal treatment across pages."""
import unittest
from decimal import Decimal as D

from auto_riepilogo import costruisci_tabella_auto
from costi_tabella import _proietta, _tabella
from fatturato import riepilogo


class CoerenzaAnnuale(unittest.TestCase):
    def test_completed_vehicle_categories_match_actuals_in_future_years(self):
        category = dict(id='c', code='carburante', name='Carburante', vat_rate='.22',
                        vat_deductible_rate='1', cost_deductible_rate='.8')
        for year in (2027, 2028, 2035, 2040):
            for code, label in [('carburante', 'Carburante'), ('autostrada', 'Autostrada'), ('rate_auto', 'Rate auto')]:
                cat = {**category, 'code': code, 'name': label}
                rows = [dict(category_id='c', vehicle_id='v', expense_date=f'{year}-{month:02}-01',
                             gross_amount='122' if month % 2 else '0', amount_includes_vat=True,
                             vat_rate='.22', vat_deductible_rate='1', cost_deductible_rate='.8')
                        for month in range(1, 13)]
                # An imported invoice line can carry a different rate and no vehicle reference.
                rows.append({**rows[0], 'vehicle_id': None, 'gross_amount': '100',
                             'vat_rate': '0', 'vat_deductible_rate': '0'})
                totals = {}
                with self.subTest(year=year, category=code):
                    table, incomplete, _ = _tabella({code: cat}, {}, rows, [], [],
                        aliquota_leasing=D('.6'), totali_output=totals)
                    auto = costruisci_tabella_auto([], rows, [cat], None)
                    self.assertFalse(incomplete)
                    self.assertEqual(totals['lordo'], D('832'))
                    self.assertEqual(totals['iva'], D('132'))
                    self.assertEqual(totals['netto'], D('700'))
                    self.assertEqual(totals['deducibile'], D('420') if code == 'rate_auto' else D('560'))
                    self.assertEqual(auto[-1][label], auto[-2][label])
                    self.assertEqual(table[0]['Registrato'], table[0]['Totale annuo stimato'])
                    rows = rows[:3] + [rows[-1]]
                    actual, forecast = _proietta(rows)
                    self.assertEqual(forecast, actual / 3 * 12)

    def test_annual_estimate_excluding_vat_is_valid_and_keeps_actuals_visible(self):
        cat = dict(id='c', name='Commercialista', vat_rate='.22', vat_deductible_rate='1', cost_deductible_rate='1')
        estimates = {'c': dict(estimated_gross_amount='1000', amount_includes_vat=False)}
        costs = [dict(category_id='c', gross_amount='500')]
        totals = {}
        rows, incomplete, _ = _tabella({'commercialista': cat}, estimates, costs, [], [], totali_output=totals)
        self.assertFalse(incomplete)
        self.assertEqual(totals['deducibile'], D('1000'))
        self.assertEqual(totals['iva'], D('0'))
        self.assertEqual(next(r for r in rows if r['Voce'] == 'Commercialista')['Registrato'], '500,00 €')

    def test_revenue_forecast_converges_for_each_principal_including_zero_months(self):
        principals = [dict(id='a', name='A'), dict(id='b', name='B')]
        rows = [dict(principal_id=principal['id'], month=month, amount='0' if month == 1 else str(month * 100))
                for principal in principals for month in range(1, 13)]
        details, actual, forecast = riepilogo(principals, rows)
        self.assertEqual(actual, forecast)
        self.assertTrue(all(r['totale'] == r['stima'] and r['mesi'] == 12 for r in details))
