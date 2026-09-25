import unittest
from decimal import Decimal as D

from ammortamenti import quota_ammortamento, _coefficiente
from calcoli_fiscali import deduzione_agenti, calcola_inps_previsionale
from imposte_parametri import GRUPPI

P={r[0]:D(r[2]) for _,g in GRUPPI for r in g}

class ModelloDefinitivo2027(unittest.TestCase):
    def test_deduzione_agenti_del_modello(self):
        self.assertEqual(
            deduzione_agenti(D("105161.718168823307"),
                              P["agenti_soglia_1_foglio"],P["agenti_aliquota_1_foglio"],
                              P["agenti_soglia_2_foglio"],P["agenti_aliquota_2_foglio"],
                              P["agenti_soglia_3_foglio"],P["agenti_aliquota_3_foglio"]),
            D("976.10345"))

    def test_inps_non_sottrae_enasarco(self):
        r=calcola_inps_previsionale(
            D("115200"),D("10038.281831176693"),
            fisso=P["inps_fisso_foglio"],minimale=P["inps_minimale_foglio"],
            aliquota_prima=P["inps_aliquota_prima_foglio"],
            soglia_seconda=P["inps_soglia_seconda_foglio"],
            aliquota_seconda=P["inps_aliquota_seconda_foglio"],
            massimale=P["inps_massimale_foglio"],
            agenti=(P["agenti_soglia_1_foglio"],P["agenti_aliquota_1_foglio"],
                    P["agenti_soglia_2_foglio"],P["agenti_aliquota_2_foglio"],
                    P["agenti_soglia_3_foglio"],P["agenti_aliquota_3_foglio"]))
        self.assertEqual(r["imponibile_inps"],D("104185.614718823307"))

    def test_bene_minore_integrale(self):
        self.assertEqual(quota_ammortamento(D("500"),D(".20"),2027,2027),(D("500"),D("500")))
        self.assertEqual(quota_ammortamento(D("500"),D(".20"),2027,2028),(D("0"),D("500")))

    def test_coefficiente_dimezzato_primo_anno(self):
        q1,f1=quota_ammortamento(D("1000"),D(".20"),2027,2027)
        q2,f2=quota_ammortamento(D("1000"),D(".20"),2027,2028)
        self.assertEqual((q1,f1),(D("100"),D("100")))
        self.assertEqual((q2,f2),(D("200"),D("300")))

    def test_coefficiente_non_richiesto_sotto_soglia(self):
        self.assertEqual(_coefficiente("", D("516.46")), D("1"))
        with self.assertRaises(ValueError):
            _coefficiente("", D("516.47"))

if __name__=="__main__":
    unittest.main()
