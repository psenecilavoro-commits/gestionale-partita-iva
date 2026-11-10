import unittest
from decimal import Decimal as D
from accantonamenti_iva import calcola_saldi_mensili,iva_vendite_mensile,iva_vendite_ibrida
from accantonamenti_completi import calcola_tabella_completa

class NettoIVA(unittest.TestCase):
 def invoice(self,month,vat):
  day=f'2027-{month:02d}-01'
  return dict(operation_date=day,received_date=day,registered_date=day,anticipate=False,category='altro',vat_amount=vat,deductible_vat=vat)
 def test_bank_receipt_minus_reserve_minus_net_vat_not_plus_credit_twice(self):
  sales=[dict(month=1,amount='9090.91')]
  invoices=[self.invoice(1,'500')]
  iva=calcola_saldi_mensili(sales,invoices,2027)
  self.assertEqual(iva[1]['vendite'],D('2000.00'));self.assertEqual(iva[1]['debito'],D('1500'))
  rows,_,_,total,complete=calcola_tabella_completa(sales,[dict(month=1,reserved_amount='3000')],[dict(month=1,amount='10000')],iva)
  self.assertEqual(rows[0]['Provvigioni nette IVA inclusa'],'10.000,00 €')
  self.assertEqual(rows[0]['Provvigioni nette - accantonato'],'5.500,00 €');self.assertEqual(total,D('5500'));self.assertEqual(complete,1)
 def test_forfettario_unchanged_and_missing_vat_or_incomes_stay_missing(self):
  reserves=[dict(month=1,reserved_amount='3000')];net=[dict(month=1,amount='10000')]
  rows,_,_,total,_=calcola_tabella_completa([],reserves,net)
  self.assertEqual(rows[0]['Provv. nette − accantonato · prima IVA'],'7.000,00 €');self.assertEqual(total,D('7000'))
  rows,_,_,_,complete=calcola_tabella_completa([],reserves,net,{})
  self.assertEqual(rows[0]['Provvigioni nette - accantonato'],'—');self.assertEqual(complete,0)
 def test_excess_credit_carried_not_spendable_then_consumed_once(self):
  sales=[dict(month=1,amount='1000'),dict(month=2,amount='1000'),dict(month=3,amount='1000')]
  iva=calcola_saldi_mensili(sales,[self.invoice(1,'500')],2027)
  self.assertEqual((iva[1]['debito'],iva[1]['credito']),(D('0'),D('280')))
  self.assertEqual((iva[2]['debito'],iva[2]['credito']),(D('0'),D('60')))
  self.assertEqual((iva[3]['debito'],iva[3]['credito']),(D('160'),D('0')))
  missing=calcola_saldi_mensili([sales[0],sales[2]],[self.invoice(1,'500')],2027)
  self.assertIsNone(missing[3]['debito'])
 def test_gross_metadata_retains_original_cent_and_is_not_resplit_from_bank_receipt(self):
  sales=[dict(month=1,amount='.84',notes='\n[PIVA_GROSS_22_V1]1.03')]
  self.assertEqual(iva_vendite_mensile(sales)[1],D('.19'))

 def test_hybrid_vat_uses_document_month_and_only_the_manual_remainder(self):
  importazione = dict(direction="emessa", economic_year_id="y", document_year_id="y",
                      record_ids={"sale": "s", "revenue": "r"})
  documento = dict(id="s", taxable_amount="1000", vat_amount="220.01", vat_month=1)
  incasso = dict(id="r", month=2, amount="1500")
  vendite = iva_vendite_ibrida([incasso], [importazione], [documento], "y")
  self.assertEqual(vendite, {1: D("220.01"), 2: D("110")})
  saldi = calcola_saldi_mensili([incasso], [self.invoice(1,"250")], 2027, vendite=vendite)
  self.assertEqual(saldi[2]["debito"], D("80.01"))
  with self.assertRaisesRegex(ValueError, "inferiore"):
   iva_vendite_ibrida([{**incasso, "amount": "999"}], [importazione], [documento], "y")

 def test_hybrid_vat_handles_invoice_and_receipt_in_different_years(self):
  importazione = dict(direction="emessa", economic_year_id="2028", document_year_id="2027",
                      record_ids={"sale": "s", "revenue": "r"})
  documento = dict(id="s", taxable_amount="1000", vat_amount="220", vat_month=12)
  incasso = dict(id="r", month=1, amount="1000")
  self.assertEqual(iva_vendite_ibrida([], [importazione], [documento], "2027"), {12: D("220")})
  self.assertEqual(iva_vendite_ibrida([incasso], [importazione], [documento], "2028"), {1: D("0")})


 def test_pending_sale_has_documentary_vat_without_cash_revenue(self):
  pending = dict(direction="emessa", economic_year_id=None, document_year_id="y",
                 record_ids={"sale": "s", "revenue": None})
  sale = dict(id="s", taxable_amount="1000", vat_amount="220", vat_month=1)
  self.assertEqual(iva_vendite_ibrida([], [pending], [sale], "y"), {1: D("220")})


if __name__=='__main__':unittest.main()
