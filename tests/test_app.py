"""Smoke test Streamlit senza rete: database finto, nessuna credenziale."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from streamlit.testing.v1 import AppTest


class Query:
    def __init__(self, table, status="open", missing=False):
        self.table = table
        self.status = status
        self.missing = missing
    def select(self, *_): return self
    def eq(self, *_): return self
    def order(self, *_): return self
    def limit(self, *_): return self
    def range(self, *_): return self
    def execute(self):
        if self.missing and self.table in ("sales_vat_invoices", "vat_periods", "pension_payments", "purchase_cost_links"):
            exc = RuntimeError("missing")
            exc.code = "PGRST205"
            raise exc
        return SimpleNamespace(data=[{"id": "anno", "fiscal_year": 2027, "status": self.status}] if self.table == "fiscal_years" else [])


class AppSmoke(unittest.TestCase):
    def test_form_vendita_richiede_conferma_e_salva_importi(self):
        script = '''
from datetime import date
from struttura_ui import mostra_vendite
mostra_vendite(None, {"id": "test", "fiscal_year": date.today().year, "status": "open"})
'''
        with patch("struttura_ui._carica", return_value=[]), patch("mandanti.elenco_mandanti", return_value=[{"id": "m", "name": "Mandante"}]), patch("struttura_ui.salva") as scrivi:
            app = AppTest.from_string(script).run()
            for widget, valore in zip(app.text_input, ("F/1", "100,00", "22,00")):
                widget.set_value(valore)
            app.button[0].click().run()
            scrivi.assert_not_called()
            self.assertTrue(any("Conferma" in x.value for x in app.warning))
            app.checkbox[1].check()
            app.button[0].click().run()
            self.assertEqual(list(app.exception), [])
            scrivi.assert_called_once()
            self.assertEqual(scrivi.call_args.args[3]["vat_amount"], "22.00")
            self.assertEqual(scrivi.call_args.args[3]["taxable_amount"], "100.00")

    def run_app(self, status="open", missing=False, logged=True):
        client = SimpleNamespace(table=lambda table: Query(table, status, missing))
        with patch("auth.get_client", return_value=client), patch("auth.current_user", return_value=SimpleNamespace(email="test@example.invalid") if logged else None):
            return AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20).run()

    def test_tutte_le_sezioni_vuote(self):
        app = self.run_app()
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.tabs), 7)
        self.assertTrue(any("IVA vendite" in x.value for x in app.subheader))

    def test_migrazioni_assenti_degradano_senza_crash(self):
        app = self.run_app(missing=True)
        self.assertEqual(list(app.exception), [])
        self.assertTrue(any("SQL_COMPLETAMENTO" in x.value for x in app.info))

    def test_anno_chiuso_nessun_form_nuovi_registri(self):
        app = self.run_app(status="closed")
        self.assertEqual(list(app.exception), [])
        self.assertFalse(any(x.label == "Conferma documento IVA" for x in app.button))

    def test_login_non_espone_registri(self):
        app = self.run_app(logged=False)
        self.assertEqual(list(app.exception), [])
        self.assertEqual(len(app.tabs), 0)
        self.assertTrue(any(x.label == "Password" for x in app.text_input))


if __name__ == "__main__":
    unittest.main()
