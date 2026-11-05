"""Exercise annual ledgers through the real forecast and reserve calculation."""
import json
from pathlib import Path
from decimal import Decimal as D
from unittest import TestCase
from unittest.mock import patch

from conto_economico import valori_conto_corrente
from accantonamenti_confronto import _obiettivo_ordinario, ripartisci_residuo
from oneri_annuali import _nota


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
