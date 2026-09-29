#!/usr/bin/env python3
"""Regenerate the committed DEFAULT lane guides in docs/.

The guide itself now lives in `missiongen/aar_guide.py` and is built per
request for whatever combination the pilot picked in the wizard. What this
script writes is only the default — the boom lane in an F-16C behind a KC-135,
the probe lane in a Hornet behind a KC-130 — which is what `/api/track/<id>/
guide.pdf` serves when nobody has chosen anything yet.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from missiongen import __version__, aar_guide            # noqa: E402
from missiongen.resolver import load_json                # noqa: E402


def main():
    for tid, tr in load_json("tracks").items():
        if tid.startswith("_"):
            continue
        print(aar_guide.build(tid, tr, __version__),
              aar_guide.markdown(tid, tr, __version__))


if __name__ == "__main__":
    main()
