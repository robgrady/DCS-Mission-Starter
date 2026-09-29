#!/usr/bin/env python3
"""Composite the coached-B'NAI cue cards from the squadron's own drawing.

IDEMPOTENT. Deletes nothing it does not rewrite.

WHY COMPOSITE AND NOT DRAW
--------------------------
The obvious card is a clean vector diagram of a pop-up with an arrow on it.
That card would be prettier and it would be a SECOND source of truth for the
geometry — one nobody could check against the document, drifting from the
squadron's drawing the moment anyone tidied it.

So the card IS the squadron's drawing, cropped to the panel that matters, with
one red ring showing where you are and one word saying what to do. The ring and
the word are ours and are obviously ours; every line underneath them is the
70th's.

THE RING POSITIONS ARE MEASURED, NOT GUESSED
--------------------------------------------
Each coordinate below was placed against the 846x1120 scan and checked by
rendering every ring at once and looking at it — `tests/test_wk_coach.py`
re-asserts that every ring lands on INK rather than on white space, which is
the failure a coordinate typo actually produces. A ring in the margin looks
deliberate and teaches the wrong point.

Usage:  PYTHONPATH=.:vendor python3 scripts/build_wk_coach_cards.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from PIL import Image, ImageDraw, ImageFont      # noqa: E402

from missiongen import wk, wk_coach              # noqa: E402

FONTS = ROOT / "missiongen" / "data" / "brand" / "fonts"
SRC = wk.diagram_path("bnai")
OUT = ROOT / "missiongen" / "data" / "wk_coach"

# The two panels on the page. The attack geometry is drawn above; the egress
# options are a separate figure below with its own title.
PANEL_ATTACK = (112, 95, 812, 655)
PANEL_EGRESS = (15, 800, 290, 1118)

# Where the ring goes, in SOURCE pixels, and which panel that point lives on.
MARKS = {
    "run_in":  ((381, 575), PANEL_ATTACK),   # inbound, below the split
    "split":   ((381, 548), PANEL_ATTACK),   # the two aircraft symbols
    "pup":     ((405, 515), PANEL_ATTACK),   # lead's PUP tick, CL 30
    "rollin":  ((500, 424), PANEL_ATTACK),   # ROLL-IN on the right track
    "apex":    ((508, 368), PANEL_ATTACK),   # APEX on the right track
    "track":   ((497, 318), PANEL_ATTACK),   # TRACK POINT on the right track
    "pullout": ((381, 240), PANEL_ATTACK),   # the target itself
    "egress":  ((165, 885), PANEL_EGRESS),   # the 30-degree egress figure
}

# One punch-hole remnant the diagram extractor's size filter did not catch,
# in SOURCE coordinates. It is a hole in the paper, not a line in the drawing,
# and at card scale it sits next to the egressing wingman where it reads as a
# symbol. Painted out here rather than in `build_wk_diagrams.py` because the
# shipped diagram is what it is and re-tuning that filter is how the lettering
# got eaten last time.
WHITEOUT = [(12, 1040, 54, 1092)]

W, H = 900, 760
BAND = 205                       # the directive band at the foot of the card
RING_R = 26
INK = (17, 17, 17)
# Every palette the ring is offered in. Red is the original and keeps the
# original file names; every other color gets its name in the file name
# (`wk_coach_green_<key>.png`), matching `wk_coach.card_path` — the two lists
# must agree, and `wk_coach.RINGS` is the source of truth.
RINGS = {"red": (200, 24, 24), "green": (0, 150, 60)}
PAPER = (255, 255, 255)


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_card(key: str, marker: str, directive: str,
               call: str, ring: str = "red") -> pathlib.Path:
    (mx, my), panel = MARKS[marker]
    src = Image.open(SRC).convert("RGB")

    # ring first, in SOURCE coordinates, so the crop and the scale cannot
    # drift apart — one transform instead of two.
    d = ImageDraw.Draw(src)
    for box in WHITEOUT:
        d.rectangle(box, fill=PAPER)
    d.ellipse([mx - RING_R, my - RING_R, mx + RING_R, my + RING_R],
              outline=RINGS[ring], width=6)

    crop = src.crop(panel)
    room_w, room_h = W - 40, H - BAND - 30
    k = min(room_w / crop.width, room_h / crop.height)
    crop = crop.resize((max(1, int(crop.width * k)),
                        max(1, int(crop.height * k))), Image.LANCZOS)

    card = Image.new("RGB", (W, H), PAPER)
    card.paste(crop, ((W - crop.width) // 2, 20))

    dr = ImageDraw.Draw(card)
    y0 = H - BAND
    dr.rectangle([0, y0, W, H], fill=INK)

    # The directive, as large as it will go. This is the part read in the pop.
    f_big = _font("BarlowCondensed-ExtraBold.ttf", 108)
    while dr.textlength(directive, font=f_big) > W - 60 and f_big.size > 40:
        f_big = _font("BarlowCondensed-ExtraBold.ttf", f_big.size - 4)
    dr.text(((W - dr.textlength(directive, font=f_big)) / 2, y0 + 14),
            directive, font=f_big, fill=PAPER)

    # The call, small, underneath. Read on the ground or in the egress.
    f_small = _font("SourceSans3-VF.ttf", 27)
    y = y0 + 20 + f_big.size + 8
    for line in _wrap(dr, call, f_small, W - 80)[:3]:
        dr.text(((W - dr.textlength(line, font=f_small)) / 2, y),
                line, font=f_small, fill=(226, 226, 226))
        y += 34

    out = OUT / (f"wk_coach_{key}.png" if ring == "red"
                 else f"wk_coach_{ring}_{key}.png")
    OUT.mkdir(parents=True, exist_ok=True)
    card.save(out, optimize=True)
    return out


def main():
    if not SRC or not SRC.is_file():
        raise SystemExit(f"source diagram missing: {SRC}")
    # One card per PHASE, not per ring position. Four ring positions are used
    # by more than one phase (the split serves the trail set and the IP turn;
    # the track point serves tracking and release), and the DIRECTIVE is the
    # part read in the pop. Sharing a card between two phases would mean
    # showing "TRACK" at the moment the pilot is meant to pickle.
    # Unpacked by INDEX, not by shape. A fixed-width unpack here is what broke
    # this generator the moment `PHASES` grew a fifth field for the
    # prerequisite: the script died with a ValueError, `release.sh` swallowed
    # it, and the committed cards were only still correct because nothing had
    # changed their words yet.
    # The palettes come from wk_coach.RINGS, not a list here — a color the
    # mission generator can ask for that this script does not build is a
    # FileNotFoundError in somebody's download.
    for ring in wk_coach.RINGS:
        if ring not in RINGS:
            raise SystemExit(f"wk_coach.RINGS wants {ring!r}; no color here")
        for ph in wk_coach.PHASES:
            key, marker, directive, call = ph[0], ph[1], ph[2], ph[3]
            p = build_card(key, marker, directive, call, ring)
            print(f"  {p.relative_to(ROOT)}  {directive}")
    print(f"{len(wk_coach.RINGS)} palettes x {len(wk_coach.PHASES)} cards over "
          f"{len(set(ph[1] for ph in wk_coach.PHASES))} ring positions")


if __name__ == "__main__":
    main()
