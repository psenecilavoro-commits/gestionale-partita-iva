import unittest
from decimal import Decimal as D

from forfettario_2026 import calcola_modello_2026
from regime_fiscale import regime_fiscale, e_forfettario


class TestForfettario2026(unittest.TestCase):
    def setUp(self):
        self.p = {
            "forfettario_coeff_redditivita": D("0.62"),
            "forfettario_aliquota_sostitutiva": D("0.15"),
            "forfettario_limite_ragguagliato": D("82205"),
            "forfettario_limite_uscita_immediata": D("100000"),
            "forfettario_mesi_proiezione": D("11"),
            "forfettario_contributi_ap": D("0"),
            "forfettario_riduzione_inps": D("0.35"),
            "inps_fisso_foglio": D("3031.76"),
            "inps_minimale_foglio": D("18808.01"),
            "inps_aliquota_prima_foglio": D("0.2448"),
            "inps_soglia_seconda_foglio": D("56224"),
            "inps_aliquota_seconda_foglio": D("0.2548"),
            "enasarco_tasso_foglio": D("0.085"),
            "enasarco_massimale_pluri": D("30478"),
        }

    def test_regime_per_anno(self):
        self.assertTrue(e_forfettario(2026))
        self.assertEqual(regime_fiscale(2026), "forfettario")
        self.assertEqual(regime_fiscale(2027), "ordinario")

    def test_riproduce_il_foglio_2026(self):
        r = calcola_modello_2026(
            fatturato_registrato=D("78816.98"),
            mesi_compilati=8,
            costi_annui=D("12917.49933"),
            enasarco=D("5305.7935"),
            p=self.p,
        )
        self.assertEqual(r["proiezione_12_mesi"], D("118225.4700"))
        self.assertEqual(r["fatturato_stimato"], D("108373.3475"))
        self.assertEqual(r["redditivita"], D("67191.475450"))
        self.assertEqual(r["inps_eccedente"], D("11953.9470966600"))
        self.assertEqual(r["inps_eccedente_agevolato"], D("7770.065612829000"))
        self.assertEqual(r["inps_totale"], D("10801.825612829000"))
        self.assertEqual(r["inps_senza_riduzione_eccedente"], D("14985.7070966600"))
        self.assertEqual(r["imposta_sostitutiva"], D("9623.95731750"))
        self.assertEqual(r["netto"], D("69724.271739671000"))
        self.assertEqual(r["netto_senza_riduzione_eccedente"], D("65540.3902558400"))


if __name__ == "__main__":
    unittest.main()
