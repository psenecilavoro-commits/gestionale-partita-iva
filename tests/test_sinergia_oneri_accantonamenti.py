"""Exercise annual ledgers through the real forecast and reserve calculation."""
import json
from pathlib import Path
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch

from conto_economico import valori_conto_corrente
from accantonamenti_confronto import _obiettivo_ordinario, ripartisci_residuo
from oneri_annuali import _nota, carica_oneri
from ammortamenti import calcola_bene


class Sinergia(TestCase):
    def test_ledgers_update_forecast_and_remaining_reserve_without_duplicates(self):
        fixture = json.loads((Path(__file__).parents[1] / 'web/public/demo.json').read_text())
        year = {'id': 'demo-year-2027', 'fiscal_year': 2027, 'status': 'open'}
        params = {r['code']: r for r in fixture['fiscal_parameters'] if r['fiscal_year_id'] == year['id']}
        records = {'tax_credits': [], 'tax_deductions': [], 'pension_payments': [], 'depreciable_assets': []}
        def read(client, table, **kwargs):
            return records[table]
        with patch('conto_economico.leggi_parametri', return_value=params), \
             patch('conto_economico.elenco_mandanti', return_value=[]), \
             patch('conto_economico.leggi_fatturato', return_value=[]), \
             patch('conto_economico.riepilogo', return_value=([], D('0'), D('100000'))), \
             patch('conto_economico.calcola_confronto', return_value=([], D('5000'), False)), \
             patch('conto_economico.totali_annui_previsionali', return_value={'iva': D('0'), 'netto': D('10000'), 'deducibile': D('10000')}), \
             patch('oneri_annuali.leggi_tutti', side_effect=read), \
             patch('accantonamenti_confronto.st.session_state', {}):
            def calculate():
                return valori_conto_corrente(None, year, D('8000'), D('99999')), _obiettivo_ordinario(None, year)[0]
            base, target = calculate()
            records['tax_credits'].append(dict(description='Casa', original_amount='10000', credit_rate='.5', installment_count=10, first_fiscal_year=2027, notes=_nota('Casa')))
            credited, target_credit = calculate()
            self.assertEqual(base['IMPOSTE_NETTE'] - credited['IMPOSTE_NETTE'], D('500'))
            self.assertEqual(target - target_credit, D('500'))
            records['tax_deductions'].append(dict(description='Fondo pensione', amount='5300', notes=_nota('Fondo pensione')))
            records['pension_payments'].append(dict(description='Pensione', amount='5300'))
            deducted, target_deduction = calculate()
            self.assertEqual(deducted['B16'], D('5300'))
            self.assertEqual(credited['B9'] - deducted['B9'], D('5300'))
            self.assertLess(target_deduction, target_credit)
            self.assertEqual(deducted['B11'], base['B11'])
            allocation = ripartisci_residuo(target_deduction, D('5000'), 5)
            self.assertEqual(allocation['quota_mensile'], (target_deduction - D('5000')) / 7)
            records['tax_credits'].clear()
            _, after_delete = calculate()
            self.assertEqual(after_delete - target_deduction, D('500'))
            asset = dict(description='Computer', gross_amount='12200', deductible_vat='2200',
                         first_fiscal_year=2027, depreciation_rate='.2', is_planned=False)
            records['depreciable_assets'].append(asset)
            for fiscal_year, expected in [(2027, '1000'), (2028, '2000'), (2032, '1000'), (2033, '0'), (2040, '0')]:
                with self.subTest(year=fiscal_year):
                    year['fiscal_year'] = fiscal_year
                    quota = D(expected)
                    ledger = carica_oneri(None, year)
                    forecast, _ = calculate()
                    self.assertEqual(calcola_bene(asset, fiscal_year)['quota'], quota)
                    self.assertEqual(ledger['quota_beni'], quota)
                    self.assertEqual(forecast['COSTI_DEDUCIBILI'], D('10000') + quota)
                    self.assertEqual(forecast['B13'], D('10000') + quota)
                    self.assertEqual(forecast['B15'], D('0'))
                    self.assertEqual(len(ledger['ammortamenti']), int(quota > 0))
            year['fiscal_year'] = 2027
            asset['depreciation_rate'] = '.4'
            self.assertEqual(calculate()[0]['COSTI_DEDUCIBILI'], D('12000'))
            records['depreciable_assets'].clear()
            self.assertEqual(calculate()[0]['COSTI_DEDUCIBILI'], D('10000'))
