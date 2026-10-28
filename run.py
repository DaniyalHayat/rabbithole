"""Rebuild RabbitHole from cached public snapshots."""
import runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
runpy.run_path(str(ROOT/'scripts/build.py'),run_name='__main__')
