import json
import unittest
from pathlib import Path
from datetime import date
from decimal import Decimal as D, ROUND_HALF_UP
from types import SimpleNamespace
from unittest.mock import Mock, patch

from struttura_calcoli import (contributi_per_cassa, scenario_cassa, saldo_iva,
                              valida_vendita, valida_periodo)
from registri import leggi_tutti, salva, denaro
from fatturato import riepilogo, importo_valido
from imposte_parametri import GRUPPI
from conto_economico import calcola_conto_foglio, detrazioni_anteprima_foglio
from auto_rate import quota_deducibile_test
from imposte_enasarco import calcola_confronto
from accantonamenti_confronto import obiettivo_annuo_foglio, quota_mesi_vuoti_foglio

PARAMETRI = {r[0]: D(r[2]) for _, gruppo in GRUPPI for r in gruppo}


class FormuleFoglio(unittest.TestCase):
    def test_conto_economico_tutte_le_celle(self):
        fixture = json.loads((Path(__file__).parent / "formule_foglio.json").read_text(encoding="utf-8"))["cells"]
        mandanti = [{"id": str(i), "name": str(i), "enasarco_relationship": "plurimandatario"} for i in range(4)]
        ricavi = [{"principal_id": str(i), "month": 1, "amount": valore} for i, valore in enumerate((7000, 1000, 1100, 500))]
        _, maturato, fatturato = riepilogo(mandanti, ricavi)
        _, enasarco, _ = calcola_confronto(mandanti, ricavi, D(".085"), PARAMETRI["enasarco_massimale_pluri"])
        self.assertEqual(maturato, D(9600))
        self.assertEqual(fatturato, D(115200))
        self.assertEqual(enasarco, D("5242.63"))
        iva = sum((D(v) * D(22) / D(122) for v in (8040, 2400, 600, 500, 3000)), D(0))
        netto = D("15941.83") - iva
        deducibili = (quota_deducibile_test(D(8040)) +
                      sum((D(v) / D("1.22") * D(".8") for v in (2400, 600, 500)), D(0)) +
                      D("340.97") * D(".8") + D("1060.86") * D(".8") + D(3000) / D("1.22"))
        valori = calcola_conto_foglio(fatturato, iva, netto, deducibili, enasarco,
                                      D(8000), D(5300), detrazioni_anteprima_foglio(), PARAMETRI)
        attesi = {
            "B1": D("115200"), "B5": D("25344"), "B6": D("22722.03"),
            "DED_AGENTI": D("976.10"), "B8": D("104185.61"),
            "B9": D("81031.34"), "B11": D("25991.70"), "B12": D("5242.63"),
            "B13": D("13319.86"), "B14": D("28688.41"), "B15": D("2941.51"),
            "B16": D("5300"), "B18": D("44898.91"), "B19": D("3741.58"),
            "B21": D("58218.77"), "B22": D("4851.56"),
        }
        for cella, atteso in attesi.items():
            with self.subTest(cella=cella):
                self.assertEqual(valori[cella].quantize(D(".01"), rounding=ROUND_HALF_UP), atteso)

    def test_avanzo_ap_e_mesi_vuoti(self):
        self.assertEqual(obiettivo_annuo_foglio(D(1000), D(300), D(200), D(10), D(5), D(50)), D(350))
        self.assertEqual(quota_mesi_vuoti_foglio(D(350), D(0), 1), D(350) / 11)
        self.assertIsNone(quota_mesi_vuoti_foglio(D(350), D(350), 12))

    def test_zero_conta_vuoto_no(self):
        m = [{"id": "a", "name": "A"}]
        self.assertIsNone(riepilogo(m, [])[2])
        righe = [{"principal_id": "a", "month": 1, "amount": 100}, {"principal_id": "a", "month": 2, "amount": 0}]
        self.assertEqual(riepilogo(m, righe)[2], D(600))
        with self.assertRaises(ValueError):
            riepilogo(m, righe + [righe[0]])
        with self.assertRaises(ValueError):
            riepilogo([], righe)


class CalcoliDocumentali(unittest.TestCase):
    def test_contributi_per_data_non_competenza_e_senza_doppioni(self):
        righe = [{"notes": "CONTRIBUTI_VERSATI_V1|INPS|2026", "payment_date": "2027-01-01", "amount": "8000"},
                 {"notes": "CONTRIBUTI_VERSATI_V1|INPS|2027", "payment_date": "2027-02-01", "amount": "1000"},
                 {"notes": "CONTRIBUTI_VERSATI_V1|ENASARCO|2027", "payment_date": "2027-02-01", "amount": "850"},
                 {"notes": "Generica", "amount": "9999"}]
        c = contributi_per_cassa(righe, 2027, date(2027, 12, 31))
        self.assertEqual(c, {"INPS": D(9000), "INPS_AP": D(8000), "ENASARCO": D(850)})
        r = scenario_cassa(D(30000), D(1000), c, D(5300), D(5000), PARAMETRI)
        self.assertEqual(r["fatturato"], D(30000))
        self.assertEqual(r["base"], D("13736.0504"))
        with self.assertRaises(ValueError):
            contributi_per_cassa(righe, 2028, date(2028, 12, 31))
        with self.assertRaises(ValueError):
            contributi_per_cassa(righe, 2027, date(2026, 12, 31))

    def test_perdita_non_imposta_negativa(self):
        r = scenario_cassa(D(100), D(200), {"INPS": D(0), "ENASARCO": D(0)}, D(0), D(0), PARAMETRI)
        self.assertEqual(r["base"], D(-100))
        self.assertEqual(r["totale"], 0)

    def periodo(self, **kw):
        return {"month_from": 1, "month_to": 3, "frequency": "trimestrale", "opening_credit": "20",
                "adjustment": "-5", "interest_amount": "1", "paid_amount": "10",
                "payment_date": "2027-04-10", "documents_complete": True, **kw}

    def test_iva_note_credito_crediti_versamenti_separati(self):
        vendite = [{"vat_month": 1, "vat_amount": "100", "document_type": "fattura"},
                   {"vat_month": 2, "vat_amount": "30", "document_type": "nota_credito"},
                   {"vat_month": 4, "vat_amount": "9999", "document_type": "fattura"}]
        r = saldo_iva(vendite, [], self.periodo())
        self.assertEqual(r["vendite"], D(70))
        self.assertEqual(r["saldo"], D(46))
        self.assertEqual(r["residuo"], D(36))
        r = saldo_iva([], [], self.periodo(opening_credit="50", adjustment="0", interest_amount="0"))
        self.assertEqual(r["credito_prospetto"], D(50))
        self.assertEqual(r["debito_prospetto"], D(0))
        self.assertIsNone(saldo_iva([], [], self.periodo(documents_complete=False))["saldo"])

    def test_periodi_sovrapposti_date_e_trimestri(self):
        valida_periodo(self.periodo(), 2027, [], date(2027, 12, 31))
        for r, altri in ((self.periodo(), [{"month_from": 3, "month_to": 3}]),
                         (self.periodo(month_from=2), []), (self.periodo(payment_date=None), [])):
            with self.subTest(r=r), self.assertRaises(ValueError):
                valida_periodo(r, 2027, altri, date(2027, 12, 31))

    def test_vendita_importi_positivi_e_futuro(self):
        r = {"principal_id": "A", "invoice_number": "1", "invoice_date": "2027-01-01",
             "vat_month": 1, "document_type": "nota_credito", "taxable_amount": "100", "vat_amount": "22"}
        self.assertEqual(valida_vendita(r, 2027, date(2027, 1, 1))["vat_amount"], "22")
        for payload, anno, oggi in ((dict(r, vat_amount="-22"), 2027, date(2027, 1, 1)),
                                    (r, 2028, date(2028, 1, 1)), (r, 2027, date(2026, 1, 1))):
            with self.assertRaises(ValueError):
                valida_vendita(payload, anno, oggi)

    def test_importi_non_finiti_precisione_e_zero(self):
        for valore in ("NaN", "Infinity", "-1", "1.001", "99999999999999999999999"):
            with self.subTest(valore=valore), self.assertRaises(ValueError):
                denaro(valore)
        self.assertEqual(importo_valido("1.234,56"), D("1234.56"))
        self.assertEqual(denaro("0"), D(0))


class AccessoDati(unittest.TestCase):
    def test_chiavi_privilegiate_rifiutate(self):
        from auth import valida_chiave_pubblica
        import base64
        valida_chiave_pubblica("sb_publishable_test")
        for role in ("anon", "service_role"):
            payload = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
            key = "header." + payload + ".signature"
            if role == "anon":
                valida_chiave_pubblica(key)
            else:
                with self.assertRaises(ValueError):
                    valida_chiave_pubblica(key)
        with self.assertRaises(ValueError):
            valida_chiave_pubblica("sb_secret_test")

    def test_cambio_anno_elimina_conferme_e_importi(self):
        import auth
        stato = {auth._CLIENT_KEY: "client", "anno_fiscale_selezionato": 2028,
                 "iva_conferma": True, "ce_fondo_pensione": "5300"}
        with patch.object(auth.st, "session_state", stato):
            auth.reset_fiscal_inputs()
        self.assertEqual(stato, {auth._CLIENT_KEY: "client", "anno_fiscale_selezionato": 2028})

    def test_paginazione_limite_server_inferiore(self):
        class Query:
            def select(self, *_): return self
            def order(self, *_): return self
            def eq(self, *_): return self
            def range(self, start, end): self.start = start; return self
            def execute(self): return SimpleNamespace(data=[{"id": n} for n in range(self.start, min(self.start + 137, 1205))])
        client = SimpleNamespace(table=lambda _: Query())
        self.assertEqual(len(leggi_tutti(client, "test")), 1205)

    def test_blocco_anno_chiuso_e_concorrenza(self):
        client = Mock()
        query = client.table.return_value
        query.select.return_value.eq.return_value.execute.return_value.data = [{"id": "a", "fiscal_year": 2027, "status": "closed"}]
        with self.assertRaises(ValueError):
            salva(client, "sales_vat_invoices", {"id": "a", "fiscal_year": 2027}, {})
        query.insert.assert_not_called()
        with patch("registri.anno_aperto"):
            query.update.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value.data = []
            with self.assertRaises(ValueError):
                salva(client, "sales_vat_invoices", {"id": "a"}, {}, {"id": "r", "version": 3})
            query.update.return_value.eq.return_value.eq.return_value.eq.assert_called_with("version", 3)

    def test_logout_svuota_dati_anche_se_rete_fallisce(self):
        import auth
        client = Mock()
        client.auth.sign_out.side_effect = RuntimeError("offline")
        stato = {auth._CLIENT_KEY: client, "san_cache_2027": {"x": "privato"}, "ce_contributi_ap": "8000"}
        with patch.object(auth.st, "session_state", stato):
            auth.sign_out()
        self.assertEqual(stato, {})


if __name__ == "__main__":
    unittest.main()
