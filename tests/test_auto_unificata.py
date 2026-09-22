"""Regressioni della scheda Auto unificata senza anagrafica obbligatoria."""
import unittest

from auto import NOTA_VEICOLO_TEST, _km_validi, auto_unica
from auto_spese_reali import AUTO_CODICI, ETICHETTE, TIPI


class TestAutoUnificata(unittest.TestCase):
    def test_tutte_le_quattro_registrazioni_nella_stessa_maschera(self):
        self.assertEqual(TIPI, ("percorrenza", "carburante", "autostrada", "rate_auto"))
        self.assertEqual(AUTO_CODICI, ("carburante", "autostrada", "rate_auto"))
        self.assertEqual(tuple(ETICHETTE), TIPI)

    def test_selezione_automatica_auto_effettiva_senza_eliminare_demo(self):
        demo = {"id": "demo", "notes": NOTA_VEICOLO_TEST}
        effettiva = {"id": "reale", "notes": "Registrazione manuale"}
        self.assertIs(auto_unica([demo, effettiva]), effettiva)
        self.assertIs(auto_unica([demo]), demo)
        self.assertIsNone(auto_unica([]))
        with self.assertRaises(ValueError):
            auto_unica([effettiva, {"id": "seconda", "notes": "Registrazione manuale"}])

    def test_km_zero_valido_ma_vuoto_non_equivale_a_zero(self):
        self.assertEqual(str(_km_validi("0")), "0")
        self.assertEqual(str(_km_validi("1.800,50")), "1800.50")
        with self.assertRaises(ValueError):
            _km_validi("")


if __name__ == "__main__":
    unittest.main()
