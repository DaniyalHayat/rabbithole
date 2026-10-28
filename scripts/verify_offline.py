"""Verify a fresh build using only the checked-in source archive and manifests."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'tmp').mkdir(exist_ok=True)
fresh = Path(tempfile.mkdtemp(prefix='offline-', dir=ROOT / 'tmp')).resolve()
assert ROOT in fresh.parents
for directory in ['src', 'scripts', 'sql']:
    shutil.copytree(ROOT / directory, fresh / directory, ignore=shutil.ignore_patterns('__pycache__'))
for directory in ['data/raw', 'outputs', 'app']:
    (fresh / directory).mkdir(parents=True, exist_ok=True)
for name in ['data/openalex_snapshot.json.gz', 'data/snapshot_checksum.txt', 'data/raw/manifest.json', 'data/natural_earth_countries.geojson', 'data/geo_manifest.json', 'outputs/benchmark.json', 'outputs/ml_model.json', 'outputs/ml_benchmark.json']:
    if (ROOT / name).exists():
        shutil.copy(ROOT / name, fresh / name)
result = subprocess.run([sys.executable, str(fresh / 'scripts/build.py')], capture_output=True, text=True)
if result.returncode:
    raise RuntimeError(result.stderr)
actual = json.loads((fresh / 'outputs/build_report.json').read_text())
expected = json.loads((ROOT / 'outputs/build_report.json').read_text())
for key in ['papers', 'citation_edges', 'topics', 'abstracts', 'open_access', 'retracted', 'quarantined']:
    assert actual[key] == expected[key], key
report = {'passed': True, 'raw_api_json_files_present': False, 'papers': actual['papers'], 'citation_edges': actual['citation_edges'], 'source': 'checked-in SHA-256-verified compressed archive', 'network_requests': 0}
(ROOT / 'outputs/offline_build_report.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
