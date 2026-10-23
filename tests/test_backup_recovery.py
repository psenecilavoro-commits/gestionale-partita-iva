import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BackupRecovery(unittest.TestCase):
    def test_generator_maps_owner_preserves_ids_values_and_guards_empty_tables(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'ripristino').mkdir()
            shutil.copyfile(ROOT / 'web/public/backup-support/ripristina-dati.py', path / 'ripristina-dati.py')
            data = {'tables': {'fiscal_years': [{'id': 'original-id', 'user_id': 'old-owner', 'notes': "L'anno", 'amount': '0.00', 'blank': None}], 'invoice_imports': []}}
            (path / 'ripristino/dati-tutti-gli-anni.json').write_text(json.dumps(data), encoding='utf-8')
            result = subprocess.run([sys.executable, str(path / 'ripristina-dati.py')], input='00000000-0000-4000-8000-000000000001\n', text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            sql = (path / 'ripristino/ripristina-dati.sql').read_text(encoding='utf-8')
            self.assertIn('00000000-0000-4000-8000-000000000001', sql)
            self.assertNotIn('old-owner', sql)
            self.assertIn('original-id', sql)
            self.assertIn("L''anno", sql)
            self.assertIn('"amount": "0.00"', sql)
            self.assertIn('"blank": null', sql)
            self.assertIn('SELECT 1 FROM public."invoice_imports"', sql)
            self.assertTrue(sql.endswith('COMMIT;'))

    def test_invalid_owner_does_not_generate_sql(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / 'ripristino').mkdir()
            shutil.copyfile(ROOT / 'web/public/backup-support/ripristina-dati.py', path / 'ripristina-dati.py')
            (path / 'ripristino/dati-tutti-gli-anni.json').write_text('{"tables":{}}', encoding='utf-8')
            result = subprocess.run([sys.executable, str(path / 'ripristina-dati.py')], input='invalid\n', text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((path / 'ripristino/ripristina-dati.sql').exists())


if __name__ == '__main__':
    unittest.main()
