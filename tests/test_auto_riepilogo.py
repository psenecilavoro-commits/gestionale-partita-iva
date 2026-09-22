"""Regressioni della tabella mensile Auto e della voce annuale limite/penale."""
import unittest
from decimal import Decimal

from auto import _formato_km
from auto_carburante import _euro
from auto_riepilogo import COLONNE, costruisci_tabella_auto, riepilogo_limite_penale


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
        self.assertEqual(COLONNE, ("Mese", "Percorrenza", "Carburante", "Autostrada", "Rate auto"))
        self.assertNotIn("Origine", righe[0])
        self.assertNotIn("Limite km", righe[0])
        self.assertNotIn("Penale", righe[0])
        self.assertEqual(righe[0]["Carburante"], _euro(Decimal("100")))
        self.assertEqual(righe[1]["Carburante"], _euro(Decimal("80")))
        self.assertEqual(righe[1]["Percorrenza"], _formato_km(Decimal("0")))
        self.assertEqual(righe[2]["Carburante"], "—")
        self.assertEqual(righe[-2]["Mese"], "Totale registrato")
        self.assertEqual(righe[-2]["Carburante"], _euro(Decimal("180")))
        self.assertEqual(righe[-2]["Percorrenza"], _formato_km(Decimal("2000")))
        self.assertEqual(righe[-1]["Carburante"], _euro(Decimal("1080")))
        self.assertEqual(righe[-1]["Percorrenza"], _formato_km(Decimal("12000")))
        voce = riepilogo_limite_penale(km, impostazioni)
        self.assertEqual(voce["Limite annuo"], _formato_km(Decimal("10000")))
        self.assertEqual(voce["Tariffa per km eccedente"], _euro(Decimal("0.10")))
        self.assertEqual(voce["Penale su km registrati"], _euro(Decimal("0")))
        self.assertEqual(voce["Penale su km stimati"], _euro(Decimal("200")))

    def test_vuoto_non_equivale_a_zero_e_penale_non_inventata(self):
        righe = costruisci_tabella_auto([], [], [], None)
        self.assertTrue(all(val == "—" for val in righe[0].values() if val != righe[0]["Mese"]))
        self.assertEqual(riepilogo_limite_penale([], None)["Penale su km stimati"], "—")
        self.assertEqual(riepilogo_limite_penale([], None)["Limite annuo"], "—")
        self.assertEqual(riepilogo_limite_penale([], {"annual_km_limit": 50000,
                                                     "excess_km_penalty": "0.16"})["Penale su km registrati"], "—")
        self.assertEqual(riepilogo_limite_penale([{"month": 1, "distance_km": "5000"}],
                                                 {"annual_km_limit": 10000})["Penale su km stimati"], "—")

    def test_blocca_mesi_chilometrici_duplicati(self):
        with self.assertRaises(ValueError):
            costruisci_tabella_auto([{"month": 1, "distance_km": 1},
                                    {"month": 1, "distance_km": 2}], [], [], None)


if __name__ == "__main__":
    unittest.main()
