"""Test senza collegamento a Supabase o dati reali."""
import unittest
from decimal import Decimal

from fatture_acquisto_xml import estrai_fattura_xml
from iva_anteprima import periodo_detrazione
from quadro_mensile import _csv_bytes, costruisci_quadro
from datetime import date


def xml_fattura(tipo="TD01", imposte=("12.10", "2.20"), n_corpi=1):
    intestazione = """<FatturaElettronicaHeader><CedentePrestatore><DatiAnagrafici>
      <Anagrafica><Denominazione>Fornitore Prova</Denominazione></Anagrafica>
      </DatiAnagrafici></CedentePrestatore></FatturaElettronicaHeader>"""
    righe = "".join(f"<DatiRiepilogo><Imposta>{iva}</Imposta></DatiRiepilogo>" for iva in imposte)
    corpo = (f"<FatturaElettronicaBody><DatiGenerali><DatiGeneraliDocumento>"
             f"<TipoDocumento>{tipo}</TipoDocumento><Numero>F/5</Numero>"
             f"<Data>2027-01-08</Data></DatiGeneraliDocumento></DatiGenerali>"
             f"<DatiBeniServizi>{righe}</DatiBeniServizi></FatturaElettronicaBody>")
    return ("<FatturaElettronica>" + intestazione + corpo * n_corpi
            + "</FatturaElettronica>").encode("utf-8")


class TestImportXML(unittest.TestCase):
    def test_somma_iva_senza_confonderla_con_imponibile(self):
        risultato = estrai_fattura_xml(xml_fattura())
        self.assertEqual(risultato["vat_amount"], Decimal("14.30"))
        self.assertEqual(risultato["supplier"], "Fornitore Prova")
        self.assertEqual(risultato["invoice_number"], "F/5")
        self.assertEqual(risultato["invoice_date"], date(2027, 1, 8))

    def test_rifiuta_nota_credito(self):
        with self.assertRaises(ValueError):
            estrai_fattura_xml(xml_fattura(tipo="TD04"))

    def test_rifiuta_xml_con_piu_corpi(self):
        with self.assertRaises(ValueError):
            estrai_fattura_xml(xml_fattura(n_corpi=2))

    def test_iva_mancante_non_diventa_zero(self):
        risultato = estrai_fattura_xml(xml_fattura(imposte=()))
        self.assertIsNone(risultato["vat_amount"])

    def test_dtd_non_accettato(self):
        payload = b'<!DOCTYPE f [<!ENTITY x "secret">]><FatturaElettronica>&x;</FatturaElettronica>'
        with self.assertRaises(ValueError):
            estrai_fattura_xml(payload)


class TestQuadro(unittest.TestCase):
    def setUp(self):
        self.fatturati = [{"month": 1, "amount": "1000.00", "notes": None}]
        self.nette = [{"month": 1, "amount": "700.00"}]
        self.riserve = [{"month": 1, "reserved_amount": "100.00"}]
        self.acquisti = [{
            "operation_date": "2027-01-03", "received_date": "2027-01-06",
            "registered_date": "2027-01-07", "anticipate": False,
            "category": "altro", "vat_amount": "22.00", "deductible_vat": "11.00",
        }]

    def test_netto_foglio_e_solo_ipotesi(self):
        tabella, controlli = costruisci_quadro(
            self.fatturati, self.nette, self.riserve, self.acquisti, 2027
        )
        self.assertEqual(tabella[0]["Differenza IVA · ipotesi (NON dovuta)"], "209,00 €")
        self.assertEqual(tabella[0]["Netto foglio · ipotesi (NON disponibile)"], "391,00 €")
        self.assertEqual(controlli[0]["Fatture IVA acquisti registrate"], 1)
        self.assertEqual(tabella[1]["Provvigioni nette"], "—")

    def test_senza_fatture_non_inventa_iva_zero(self):
        tabella, _ = costruisci_quadro(self.fatturati, self.nette, self.riserve, [], 2027)
        self.assertEqual(tabella[0]["IVA acquisti registrata (PARZIALE)"], "—")
        self.assertEqual(tabella[0]["Netto foglio · ipotesi (NON disponibile)"], "—")

    def test_blocca_mese_nette_duplicato(self):
        with self.assertRaises(ValueError):
            costruisci_quadro(self.fatturati, self.nette + self.nette,
                             self.riserve, self.acquisti, 2027)

    def test_prova_15_del_mese_successivo(self):
        self.assertEqual(periodo_detrazione(
            date(2027, 1, 31), date(2027, 2, 15), date(2027, 2, 15)
        ), (2027, 1, True))
        self.assertEqual(periodo_detrazione(
            date(2027, 12, 31), date(2028, 1, 10), date(2028, 1, 10)
        ), (2028, 1, False))

    def test_export_blocca_formule_csv(self):
        testo = _csv_bytes([{"Fornitore": "=IMPORTRANGE(1)", "Importo": "10,00"}]).decode("utf-8-sig")
        self.assertIn("'=IMPORTRANGE(1)", testo)


if __name__ == "__main__":
    unittest.main()
