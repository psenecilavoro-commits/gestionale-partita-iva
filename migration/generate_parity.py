"""Generate a CPython oracle using unchanged fiscal modules and synthetic data."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'web/engine'))
sys.path.insert(0, str(ROOT))
import react_bridge as bridge
bridge.open = lambda path, *args, **kwargs: open(ROOT / 'app.py' if path == '/app/app.py' else path, *args, **kwargs)
tables = json.loads((ROOT / 'web/public/demo.json').read_text(encoding='utf-8'))
def project(nodes):
    values = []
    for n in nodes:
        if n['kind'] == 'metric':
            values.append({'kind': 'metric', 'label': n['label'], 'value': n['value']})
        if n['kind'] == 'table':
            values.append({'kind': 'table', 'records': n['records']})
        values.extend(project(n['children']))
    return values
results = {}
for year in (2026, 2027):
    for page in ('Fatturato', 'Costi', 'Auto', 'Accantonamenti', 'Conto economico', 'Imposte', 'Detrazioni e deduzioni', 'Ammortamenti'):
        bridge.clear_session()
        result = json.loads(bridge.render({'tables': tables, 'user': {'id': 'demo-owner', 'email': 'demo@example.invalid'}, 'inputs': {'anno_fiscale_selezionato': year, 'schede_principali': page}}))
        results[str(year) + ':' + page] = project(result['sidebar']) + project(result['tree'])
(ROOT / 'web/tests/fixtures/fiscal-parity.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('CPython oracle: 16 sections, original tables and metrics')
