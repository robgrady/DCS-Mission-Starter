"""Make `pytest` work from a bare checkout.

pydcs is vendored at `vendor/dcs` rather than installed, so every module in the
project fails at import time with `ModuleNotFoundError: No module named 'dcs'`
unless `vendor/` is on sys.path. That used to mean the suite only ran as
`PYTHONPATH=vendor pytest`, which is exactly the kind of undocumented incantation
that stops people running the tests at all.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for p in (ROOT, ROOT / "vendor"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
