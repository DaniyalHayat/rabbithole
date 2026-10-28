"""Preserve the fetched source metadata in a deterministic, offline source archive."""
import gzip, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
raw=ROOT/'data/raw'
manifest=json.loads((raw/'manifest.json').read_text(encoding='utf-8'))
payload={'manifest':manifest,'files':{e['file']:json.loads((raw/e['file']).read_text(encoding='utf-8')) for e in manifest['files']}}
path=ROOT/'data/openalex_snapshot.json.gz'
with path.open('wb') as f:
    with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as gz:gz.write(json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
(ROOT/'data/snapshot_checksum.txt').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  openalex_snapshot.json.gz\n')
print(path.name,path.stat().st_size,'bytes')
