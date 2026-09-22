"""Regressioni: le tre voci auto restano nei totali ma non nell'editor Costi."""
import unittest
from datetime import date
from decimal import Decimal

from auto_spese_reali import AUTO_CODICI, valida_spesa_auto
from costi_scheda import SOLO_AUTO, voci_modificabili
from costi_tabella import VOCI, _proietta, _tabella


class TestRipartizioneSpese(unittest.TestCase):
    def test_auto_solo_in_editor_auto_ma_presenti_nel_riepilogo(self):
        tutti = {r[0] for r in VOCI}
        annuali = {r[0] for r in voci_modificabili()}
        self.assertEqual(set(AUTO_CODICI), set(SOLO_AUTO))
        self.assertTrue(set(AUTO_CODICI).issubset(tutti))
        self.assertTrue(set(AUTO_CODICI).isdisjoint(annuali))
        self.assertTrue(all(r[2] == "annuale" for r in voci_modificabili()))
        self.assertIn("commercialista", annuali)

    def test_stima_auto_usa_stessi_record_esistenti(self):
        spese = [
            {"category_id": "c", "vehicle_id": "v", "gross_amount": "70.00",
             "expense_date": "2027-01-05", "amount_includes_vat": True},
            {"category_id": "c", "vehicle_id": "v", "gross_amount": "30.00",
             "expense_date": "2027-01-15", "amount_includes_vat": True},
            {"category_id": "c", "vehicle_id": "v", "gross_amount": "80.00",
             "expense_date": "2027-02-05", "amount_includes_vat": True},
        ]
        for spesa in spese:
            spesa.update(vat_rate="0.22", vat_deductible_rate="0.4",
                         cost_deductible_rate="0.8")
        registrato, proiezione = _proietta(spese)
        self.assertEqual(registrato, Decimal("180.00"))
        self.assertEqual(proiezione, Decimal("1080.00"))
        cat = {"id": "c", "name": "Carburante", "vat_rate": "0.22",
               "vat_deductible_rate": "0.4", "cost_deductible_rate": "0.8"}
        tabella, _incompleti, _origini = _tabella(
            {"carburante": cat}, {}, spese, [], [])
        carburante = next(r for r in tabella if r["Voce"] == "Carburante")
        self.assertNotEqual(carburante["Registrato"], "—")
        self.assertNotEqual(carburante["Totale annuo stimato"], "—")

    def test_spesa_auto_solo_anno_e_data_non_futura(self):
        valida_spesa_auto("carburante", date(2027, 1, 3), Decimal("25.00"), 2027,
                          oggi=date(2027, 1, 4))
        with self.assertRaises(ValueError):
            valida_spesa_auto("carburante", date(2027, 2, 3), Decimal("25.00"), 2027,
                              oggi=date(2027, 1, 4))
        with self.assertRaises(ValueError):
            valida_spesa_auto("carburante", date(2026, 1, 3), Decimal("25.00"), 2027,
                              oggi=date(2027, 1, 4))
        with self.assertRaises(ValueError):
            valida_spesa_auto("commercialista", date(2027, 1, 3), Decimal("25.00"), 2027,
                              oggi=date(2027, 1, 4))
        with self.assertRaises(ValueError):
            valida_spesa_auto("rate_auto", date(2027, 1, 3), Decimal("0.00"), 2027,
                              oggi=date(2027, 1, 4))


if __name__ == "__main__":
    unittest.main()
