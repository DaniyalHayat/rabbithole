"""Download reproducible, attributed research snapshots; no credentials required."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEMES = {
    'music': ['music memory emotion', 'involuntary musical imagery earworms'],
    'dreams': ['dreaming sleep memory consolidation', 'lucid dreaming consciousness'],
    'attention': ['attention distraction multitasking', 'social media attention wellbeing'],
    'connection': ['loneliness social connection', 'friendship interpersonal synchrony'],
    'creativity': ['creativity divergent thinking', 'curiosity learning information gap'],
    'habits': ['habit formation behavior change', 'procrastination self regulation'],
    'awe': ['awe nature wellbeing', 'urban green space mental wellbeing'],
    'perception': ['time perception subjective experience', 'visual perception illusions']
}
SELECT = 'id,title,doi,publication_year,publication_date,type,cited_by_count,open_access,topics,referenced_works,abstract_inverted_index,authorships,is_retracted'

def download(url: str) -> bytes:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'RabbitHole-Portfolio/1.0 (public research metadata)'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError('unreachable')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = {'retrieved_at': datetime.now(timezone.utc).isoformat(), 'provider': 'OpenAlex', 'selection': 'Top 100 relevance-ranked results for each of 16 fixed curiosity searches; not a representative literature census.', 'files': []}
    for theme, queries in THEMES.items():
        for i, query in enumerate(queries):
            params = {'search': query, 'per_page': 100, 'select': SELECT, 'filter': 'language:en,to_publication_date:2026-10-27'}
            url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(params)
            path = raw / f'{theme}_{i}.json'
            if not path.exists():
                payload = download(url)
                obj = json.loads(payload)
                if not isinstance(obj.get('results'), list):
                    raise ValueError('Unexpected OpenAlex schema')
                path.write_bytes(payload)
                time.sleep(.2)
            payload = path.read_bytes()
            entry = {'file': path.name, 'theme': theme, 'query': query, 'url': url, 'sha256': hashlib.sha256(payload).hexdigest(), 'rows': len(json.loads(payload)['results'])}
            manifest['files'].append(entry)
            print(theme, i, entry['rows'], flush=True)
    (raw / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    if args.benchmark:
        url = 'https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip'
        archive = raw / 'scifact.zip'
        if not archive.exists():
            archive.write_bytes(download(url))
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                target = (raw / info.filename).resolve()
                if raw.resolve() not in target.parents:
                    raise ValueError('Unsafe archive path')
            z.extractall(raw)
        (raw / 'benchmark_manifest.json').write_text(json.dumps({'url': url, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'source': 'BEIR SciFact; AllenAI SciFact / S2ORC. See docs/SOURCES.md for separate data licenses.'}, indent=2), encoding='utf-8')
        print('SciFact downloaded', archive.stat().st_size, flush=True)

if __name__ == '__main__':
    main()
