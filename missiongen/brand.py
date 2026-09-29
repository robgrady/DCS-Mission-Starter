"""Flightline Technical / Authentic Style — the ONE place color and type live.

AUTHENTIC STYLE v2.1 (6 Sep 2026): the DOCUMENT palette in the token file
is now the specimen Rob supplied — white paper, navy #00205B, accent
#1D4E89, panel #F4F6F8, ink #101828, dim #475467, danger/warn/ok — and the
page furniture every renderer draws comes from `missiongen/authentic.py`.
The type roles below are unchanged; the specimen uses the same six faces.

Rob adopted the Flightline kit (12 Aug 2026) with a specific instruction that
this module exists to honor: one token source, everything derived. Before
this file, the palette existed independently in the site CSS, kneeboard.py,
brief.py and chartstyle.py — four copies of a truth, which is precisely this
project's recurring failure mode (Incirlik, the roadmap, the generated pages —
every one was two copies drifting).

Renderers import COLORS and font() from here. The token file is data
(`data/brand/flightline.json`), so the palette is inspectable and testable
without importing PIL, and the site CSS generator reads the SAME file.

Fonts are the kit's five roles, vendored under data/brand/fonts (all OFL,
license texts alongside). Source Sans 3 / Source Serif 4 ship as variable
fonts; weight is set per-instance. EVERY font call degrades to DejaVu rather
than failing — a missing font must cost fidelity, never a mission.
"""
from __future__ import annotations

import functools
from pathlib import Path

from PIL import ImageFont

from .resolver import load_json

_BRAND_DIR = Path(__file__).parent / "data" / "brand"
_DEJAVU = "/usr/share/fonts/truetype/dejavu/"


@functools.lru_cache(maxsize=1)
def tokens() -> dict:
    return load_json("brand/flightline")


def _hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class _Colors:
    """Attribute access to the palette as PIL RGB tuples: `COLORS.navy`."""

    def __getattr__(self, name):
        try:
            return _hex_rgb(tokens()["colors"][name])
        except KeyError:
            raise AttributeError(f"no color token {name!r}") from None


COLORS = _Colors()

# Shape symbols for redundant state coding (MIL-STD-1472H via the kit): a
# color-blind pilot, a grayscale print and a red-lit cockpit all still read
# the state. Use next to every colored status the product renders.
SYMBOLS = {"normal": "●", "caution": "◆", "warning": "▲"}


@functools.lru_cache(maxsize=32)
def font(role: str, size: int) -> ImageFont.FreeTypeFont:
    """A PIL font for a token role at `size`, with the DejaVu fallback.

    Cached: PIL font objects are cheap but not free, and the renderers ask for
    the same handful of (role, size) pairs hundreds of times per build.
    """
    spec = tokens()["fonts"].get(role)
    if spec is None:
        raise KeyError(f"no font role {role!r} in flightline.json")
    try:
        f = ImageFont.truetype(str(_BRAND_DIR / "fonts" / spec["file"]), size)
        if "axes" in spec:
            f.set_variation_by_axes(spec["axes"])
        elif "weight" in spec:
            f.set_variation_by_axes([spec["weight"]])
        return f
    except Exception:
        try:
            return ImageFont.truetype(_DEJAVU + spec["fallback"], size)
        except Exception:
            return ImageFont.load_default()


def rail_text(subject: str, extra: str = "") -> str:
    """The identity rail line: publication · subject · revision.

    This REPLACES the v1.55.0 classification banner. The kit's research is
    explicit — avoid classification-style markings — and the rail answers the
    four questions a real publication answers on every page: what is this,
    what does it cover, what revision applies, where am I. `extra` carries the
    per-page locator ("PAGE 2 OF 4", a work-package id, a seed).
    """
    from . import __version__
    r = tokens()["identity_rail"]
    parts = [r["publication"], r["product"], subject.upper(),
             f"REV {__version__}"]
    if extra:
        parts.append(extra.upper())
    return "  ·  ".join(p for p in parts if p)
