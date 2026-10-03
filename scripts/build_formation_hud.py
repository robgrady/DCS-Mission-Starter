#!/usr/bin/env python3
"""Build the formation position-ladder cards that ship inside every coached
formation .miz (missiongen/data/formation_hud/formation_hud_<state>.png).

Same frame, same place, same size as the AAR indicator (build_aar_hud.py):
200x360, left edge, eye level, 10% of the window — the one placement ever
confirmed rendering in a cockpit (formation_hud.py tells that story).

THE PICTURE. A four-rung ladder at the top — CLOSE / SLOT / OUT / LOST — with
the rung you are on lit; a shape in the middle (chevrons for close/open,
a ball-between-datums for high/low, a tick for good, a prohibited sign for
lost); one or two words at the bottom. Color is never the only cue: each
state is also a rung, a shape and a word, so the card reads the same to a
color-blind pilot. Nothing lateral is drawn, deliberately — the mission
measures range, not side (see the brief page).

Eight states, read from formation_hud.STATES so a state added there without
art here fails the build rather than the sortie:

  danger  OPEN OUT    inside the collision band — red, urgent
  ease    EASE OFF    closing on the slot from inside
  hold    HOLD        in the slot, on speed and altitude
  high    COME DOWN   in the slot, above lead
  low     COME UP     in the slot, below lead
  power   ADD POWER   falling out of the slot
  good    STEADY      in the band on the range-only ladder
  lost    REJOIN      outside the far band — red, urgent

Reconstructed 2026-10-03 (the original died with the 1.104–1.105 build
environment). Deterministic: same code, same bytes.

    python3 scripts/build_formation_hud.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from missiongen import formation_hud as FH  # noqa: E402

OUT = FH.ASSET_DIR
W, H = 200, 360

BG = (28, 30, 36, 240)
BG_URGENT = (58, 26, 30, 240)
EDGE = (108, 120, 138, 255)
GOOD = (74, 222, 112, 255)
WARN = (255, 190, 66, 255)
BAD = (255, 92, 82, 255)
DATUM = (150, 160, 178, 255)
RUNG = (46, 50, 60, 255)
RUNG_EDGE = (70, 76, 90, 255)
INK = (240, 244, 250, 255)
GREY = (138, 146, 160, 255)

RUNGS = ["CLOSE", "SLOT", "OUT", "LOST"]      # top to bottom = near to far

# state -> (lit rung, color, words, shape, urgent)
CARDS = {
    "danger": ("CLOSE", BAD,  ("OPEN", "OUT"),   "chev_down3", True),
    "ease":   ("CLOSE", WARN, ("EASE", "OFF"),   "chev_down2", False),
    "hold":   ("SLOT",  GOOD, ("HOLD", ""),      "ball_on",    False),
    "high":   ("SLOT",  WARN, ("COME", "DOWN"),  "ball_high",  False),
    "low":    ("SLOT",  WARN, ("COME", "UP"),    "ball_low",   False),
    "power":  ("OUT",   WARN, ("ADD", "POWER"),  "chev_up2",   False),
    "good":   ("OUT",   GOOD, ("STEADY", ""),    "tick",       False),
    "lost":   ("LOST",  BAD,  ("REJOIN", ""),    "no",         True),
}
assert set(CARDS) == set(FH.STATES), set(FH.STATES) ^ set(CARDS)


def font(sz, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")
    try:
        return ImageFont.truetype(p, sz)
    except OSError:
        return ImageFont.load_default()


def _frame(urgent, edge):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, W - 3, H - 3], 12, fill=BG_URGENT if urgent else BG,
                        outline=edge if urgent else EDGE, width=3 if urgent else 2)
    return im, d


def _ladder(d, lit, col):
    f = font(10)
    for i, name in enumerate(RUNGS):
        y0 = 22 + i * 19
        on = name == lit
        d.rounded_rectangle([16, y0, W - 16, y0 + 13], 4,
                            fill=col if on else RUNG, outline=None if on else RUNG_EDGE)
        if on:
            tw = d.textlength(name, font=f)
            d.text(((W - tw) / 2, y0 + 1), name, font=f, fill=(20, 22, 26, 255))


def _ball(d, col, pos):
    cx, cy = W // 2, 196
    for x0, x1 in ((14, 58), (W - 58, W - 14)):
        d.rounded_rectangle([x0, cy - 5, x1, cy + 5], 3, fill=DATUM)
    off = {"high": -46, "on": 0, "low": 46}[pos]
    r = 24
    d.ellipse([cx - r, cy + off - r, cx + r, cy + off + r], fill=col)
    d.rounded_rectangle([cx - 13, cy + off - 4, cx + 13, cy + off + 4], 3, fill=BG[:3] + (255,))


def _tick(d, col):
    d.line([(58, 192), (92, 228), (152, 150)], fill=col, width=14, joint="curve")


def _no(d, col):
    cx, cy, r = W // 2, 196, 44
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=9)
    d.line([(cx - 30, cy - 30), (cx + 30, cy + 30)], fill=col, width=9)


def _words(d, words, col):
    big, small = font(28), font(28)
    a, b = words
    if b:
        for i, (t, c) in enumerate(((a, col), (b, INK))):
            tw = d.textlength(t, font=big)
            d.text(((W - tw) / 2, 282 + i * 34), t, font=big, fill=c)
    else:
        tw = d.textlength(a, font=big)
        d.text(((W - tw) / 2, 300), a, font=big, fill=col)


def card(state):
    rung, col, words, shape, urgent = CARDS[state]
    im, d = _frame(urgent, col)
    _ladder(d, rung, col)
    if shape.startswith("chev_down"):
        n = int(shape[-1])
        for i in range(n):
            y = 176 + (i - (n - 1) / 2) * 26
            d.polygon([(62, y - 12), (100, y + 12), (138, y - 12)], fill=col)
    elif shape.startswith("chev_up"):
        n = int(shape[-1])
        for i in range(n):
            y = 176 + (i - (n - 1) / 2) * 26
            d.polygon([(62, y + 12), (100, y - 12), (138, y + 12)], fill=col)
    elif shape.startswith("ball_"):
        _ball(d, col, shape[5:])
    elif shape == "tick":
        _tick(d, col)
    elif shape == "no":
        _no(d, DATUM)
    _words(d, words, col)
    return im


def build() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for state in FH.STATES:
        p = OUT / f"formation_hud_{state}.png"
        card(state).quantize(colors=64, method=Image.Quantize.FASTOCTREE).save(p, optimize=True)
        written.append(p)
    return written


if __name__ == "__main__":
    ps = build()
    print(f"wrote {len(ps)} cards to {OUT}")
