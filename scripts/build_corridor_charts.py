#!/usr/bin/env python3
"""Render docs/img/<map>_corridors.png + .svg — the corridor charts.

IDEMPOTENT and deterministic: same data, same bytes. Drawn by
missiongen/corridor_chart.py from data/corridors/<map>.json — the same file
the router flies and the F10 map draws — so the picture on the site cannot
disagree with the flight plan. Registered in scripts/artifacts.py: a change
to the data or the renderer without a rebuild fails the gate.

Usage:  PYTHONPATH=.:vendor python3 scripts/build_corridor_charts.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from missiongen import corridor_chart, corridors  # noqa: E402

STEMS = {"nevada": "nttr_corridors", "syria": "syria_corridors", "germany": "germany_corridors"}


def main() -> int:
    out_dir = ROOT / "docs" / "img"
    out_dir.mkdir(parents=True, exist_ok=True)
    for mk in corridors.maps():
        stem = STEMS[mk]
        img = corridor_chart.render_page(*corridor_chart.page_size(mk), mk=mk)
        img.save(out_dir / f"{stem}.png", optimize=True)
        (out_dir / f"{stem}.svg").write_text(corridor_chart.render_svg(*corridor_chart.page_size(mk), mk=mk))
        print(f"wrote docs/img/{stem}.png {img.size[0]}x{img.size[1]} and {stem}.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
