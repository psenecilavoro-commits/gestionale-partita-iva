"""Bundle unchanged, tracked production Python sources for the React renderer."""
import hashlib
import gzip
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
files = subprocess.check_output(['git', 'ls-files', '*.py'], cwd=ROOT, text=True).splitlines()
sources = {p: (ROOT / p).read_text(encoding='utf-8') for p in files if '/' not in p}
manifest = {p: hashlib.sha256(s.encode()).hexdigest() for p, s in sources.items()}
sources['react_bridge.py'] = (ROOT / 'web/engine/react_bridge.py').read_text(encoding='utf-8')
out = ROOT / 'web/public'
out.mkdir(parents=True, exist_ok=True)
(out / 'engine.json').write_text(json.dumps(sources, ensure_ascii=False), encoding='utf-8')
(out / 'engine.json.gz').write_bytes(gzip.compress(json.dumps(sources, ensure_ascii=False).encode('utf-8'), mtime=0))
(ROOT / 'migration/engine-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(f'Bundled {len(manifest)} unchanged Python modules')
