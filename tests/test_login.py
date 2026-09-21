"""Regressioni del login: vera logica auth, trasporto Supabase simulato."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest
from test_app import Query


class LoginTest(unittest.TestCase):
    def test_sessione_persa_cancella_dati_privati(self):
        import auth
        for missing in (True, False):
            with self.subTest(missing=missing):
                client = SimpleNamespace(auth=SimpleNamespace(
                    get_session=Mock(return_value=None if missing else object()),
                    get_user=Mock(side_effect=RuntimeError("Token invalid")),
                ))
                state = {auth._CLIENT_KEY: client, auth._AUTHENTICATED_KEY: True, "dato_privato": 100}
                with patch.object(auth.st, "session_state", state):
                    self.assertIsNone(auth.current_user())
                self.assertEqual(state, {})

    def test_submit_errore_riprova_accesso_e_logout(self):
        user = SimpleNamespace(email="test@example.invalid")
        state = {"logged": False}

        def get_user():
            if not state["logged"]:
                raise RuntimeError("Auth session missing")
            return SimpleNamespace(user=user)

        def login(credentials):
            if credentials["password"] != "test-password":
                raise RuntimeError("Invalid credentials")
            state["logged"] = True
            return SimpleNamespace(user=user, session=object())

        auth = SimpleNamespace(
            get_session=lambda: object() if state["logged"] else None,
            get_user=get_user,
            sign_in_with_password=Mock(side_effect=login),
            sign_out=Mock(side_effect=lambda *_: state.update(logged=False)),
        )
        client = SimpleNamespace(auth=auth, table=lambda table: Query(table))
        app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"), default_timeout=20)
        app.secrets["SUPABASE_URL"] = "https://example.supabase.co"
        app.secrets["SUPABASE_PUBLISHABLE_KEY"] = "sb_publishable_test"
        with patch("auth.create_client", return_value=client):
            app.run()
            app.text_input[0].set_value("test@example.invalid")
            app.text_input[1].set_value("wrong")
            app.button[0].click().run()
            auth.sign_in_with_password.assert_called_once()
            self.assertTrue(any("Accesso non riuscito" in x.value for x in app.error))
            self.assertEqual(len(app.tabs), 0)
            app.text_input[0].set_value("test@example.invalid")
            app.text_input[1].set_value("test-password")
            app.button[0].click().run()
            self.assertEqual(list(app.exception), [])
            self.assertEqual(len(app.tabs), 7)
            next(x for x in app.button if x.label == "Esci").click().run()
            self.assertEqual(list(app.exception), [])
            self.assertEqual(len(app.tabs), 0)
            self.assertTrue(any(x.label == "Password" for x in app.text_input))
            auth.sign_out.assert_called_once_with({"scope": "local"})
