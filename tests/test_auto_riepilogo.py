"""Regressioni della tabella mensile unificata Auto."""
import unittest
from decimal import Decimal

from auto import _formato_km
from auto_carburante import _euro
from auto_riepilogo import COLONNE, costruisci_tabella_auto


class TabellaAutoUnificata(unittest.TestCase):
    def test_dodici_mesi_senza_origine_e_somme_mensili(self):
        categorie = [{"id": "c", "code": "carburante"},
                     {"id": "a", "code": "autostrada"},
                     {"id": "r", "code": "rate_auto"},
                     {"id": "altro", "code": "commercialista"}]
        spese = [
            {"category_id": "c", "expense_date": "2027-01-04", "gross_amount": "70.00"},
            {"category_id": "c", "expense_date": "2027-01-22", "gross_amount": "30.00"},
            {"category_id": "c", "expense_date": "2027-02-03", "gross_amount": "80.00"},
            {"category_id": "a", "expense_date": "2027-01-09", "gross_amount": "50.00"},
            {"category_id": "r", "expense_date": "2027-01-01", "gross_amount": "670.00"},
            {"category_id": "altro", "expense_date": "2027-01-01", "gross_amount": "999.00"},
        ]
        km = [{"month": 1, "distance_km": "2000.00"},
              {"month": 2, "distance_km": "0.00"}]
        impostazioni = {"annual_km_limit": 10000, "excess_km_penalty": "0.10"}
        righe = costruisci_tabella_auto(km, spese, categorie, impostazioni)
        self.assertEqual(len(righe), 14)
        self.assertEqual(tuple(righe[0]), COLONNE)
        self.assertNotIn("Origine", righe[0])
        self.assertEqual(righe[0]["Carburante"], _euro(Decimal("100")))
        self.assertEqual(righe[1]["Carburante"], _euro(Decimal("80")))
        self.assertEqual(righe[1]["Percorrenza"], _formato_km(Decimal("0")))
        self.assertEqual(righe[2]["Carburante"], "—")
        self.assertEqual(righe[0]["Limite km"], "—")
        self.assertEqual(righe[0]["Penale"], "—")
        self.assertEqual(righe[-2]["Mese"], "Totale registrato")
        self.assertEqual(righe[-2]["Carburante"], _euro(Decimal("180")))
        self.assertEqual(righe[-2]["Percorrenza"], _formato_km(Decimal("2000")))
        self.assertEqual(righe[-1]["Carburante"], _euro(Decimal("1080")))
        self.assertEqual(righe[-1]["Percorrenza"], _formato_km(Decimal("12000")))
        self.assertEqual(righe[-1]["Limite km"], _formato_km(Decimal("10000")))
        self.assertEqual(righe[-1]["Penale"], _euro(Decimal("200")))

    def test_vuoto_non_equivale_a_zero_e_penale_non_inventata(self):
        righe = costruisci_tabella_auto([], [], [], None)
        self.assertTrue(all(val == "—" for val in righe[0].values() if val != righe[0]["Mese"]))
        self.assertEqual(righe[-1]["Penale"], "—")
        self.assertEqual(righe[-1]["Limite km"], "—")

    def test_blocca_mesi_chilometrici_duplicati(self):
        with self.assertRaises(ValueError):
            costruisci_tabella_auto([{"month": 1, "distance_km": 1},
                                    {"month": 1, "distance_km": 2}], [], [], None)


if __name__ == "__main__":
    unittest.main()
