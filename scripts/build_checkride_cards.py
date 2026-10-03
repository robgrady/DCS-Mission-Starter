#!/usr/bin/env python3
"""Build the check-ride debrief cards that ship inside every graded .miz
(missiongen/data/checkride/checkride_<stem>.png, 26 of them).

ONE PICTURE AT A TIME. The debrief used to be a dozen MessageToGroup lines
stacking in the DCS corner faster than anyone could read them (checkride.py
tells that story). Each of these is one card, shown centre-screen at 30% of
the window, replacing the last: an item and its grade, the rejoin, any
critical item, the overall.

EVERY NUMBER ON A CARD COMES FROM checkride.py. The 90/75/50 % ladder, the
60 m band, the 90/150/240/300 s rejoin clock, the 12 m collision band and
the 400 m / 30 s lost-wingman rule are read from the module's constants, so
a threshold edited there cannot leave the card promising the old one — the
same say/do rule the kneeboard lives by.

Reconstructed 2026-10-03 (the original died with the 1.104–1.105 build
environment). Two defects in the shipped art are fixed on the way: the big
grade letter overprinted "CLIMBS, DESCENTS, SPEED", and the collision-band
critical card's title ran off the right edge. Titles now shrink to fit the
room the letter leaves them.

    python3 scripts/build_checkride_cards.py

Deterministic: same code, same bytes.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))
from missiongen import checkride as CK  # noqa: E402

OUT = ROOT / "missiongen" / "data" / "checkride"
W, H = 560, 300

BG = (26, 29, 36, 250)
BG_CRIT = (58, 26, 30, 250)
RULE = (74, 80, 92, 255)
HEAD = (138, 146, 160, 255)
INK = (240, 244, 250, 255)
DIM = (158, 166, 180, 255)
GRADE = {"E": (73, 221, 111, 255), "G": (150, 196, 88, 255),
         "F": (255, 190, 66, 255), "U": (255, 92, 82, 255),
         "none": (124, 134, 150, 255)}


def font(sz, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")
    try:
        return ImageFont.truetype(p, sz)
    except OSError:
        return ImageFont.load_default()


def _pct(a, b):
    return int(round(100 * b / a))


# the ladder, read from the module: ("E", 10, 9) means in/tot >= 9/10
PCT = {g: _pct(a, b) for g, a, b in CK.LADDER}            # {"E": 90, "G": 75, "F": 50}
BAND = CK.POSITION_M
REJOIN = {"E": CK.REJOIN_E_S, "G": CK.REJOIN_G_S, "F": CK.REJOIN_F_S}


def item_line(grade):
    if grade == "U":
        return f"under {PCT['F']}% in the band", GRADE["U"]
    if grade == "F":
        return f"{PCT['F']}% or better — out, and corrected", GRADE["F"]
    if grade == "none":
        return "no window flown — lead never did it while you were aboard", DIM
    return f"{PCT[grade]}% or better in the band", GRADE[grade]


def rejoin_line(grade):
    if grade == "U":
        return f"longer than {REJOIN['F']} s", GRADE["U"]
    return f"inside {REJOIN[grade]} s", GRADE[grade]


CRIT = {1: ("Inside the collision band", f"within {CK.COLLISION_M} m of lead"),
        2: ("Lost wingman", f"outside {CK.LOST_M} m for {CK.LOST_S} s"),
        3: ("Never rejoined", f"not back inside {CK.REJOIN_MAX_S} s of the pitchout")}

OVERALL = {"q": ("Q", "Qualified", "Every item G or better. Record it on the gradesheet.", "E"),
           "qm": ("Q-", "Qualified with discrepancies",
                  "An item graded F. Additional training on that item.", "F"),
           "u": ("U", "Not qualified", f"An item under {PCT['F']}%. Re-fly the check.", "U"),
           "uc": ("U", "Not qualified — critical",
                  "A critical item busts the check whatever the items say.", "U")}


def _frame(edge, crit=False):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([1, 1, W - 2, H - 2], 14, fill=BG_CRIT if crit else BG,
                        outline=edge, width=3)
    return im, d


def _head(d, text):
    d.text((40, 24), text, font=font(17), fill=HEAD)
    d.line([(40, 58), (W - 36, 58)], fill=RULE, width=1)


def _wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit(d, text, max_w, start=30, floor=20):
    """The largest bold size at which `text` fits `max_w` on one line."""
    for sz in range(start, floor - 1, -1):
        f = font(sz)
        if d.textlength(text, font=f) <= max_w:
            return f
    return font(floor)


def item_card(label, grade):
    im, d = _frame(GRADE[grade])
    _head(d, "CHECK RIDE — GRADESHEET")
    # the grade letter owns the right third; the title gets what is left
    letter_w = 0 if grade == "none" else 130
    title_f = _fit(d, label.upper(), W - 40 - 40 - letter_w)
    d.text((40, 94), label.upper(), font=title_f, fill=INK)
    line, col = item_line(grade)
    y = 160
    for ln in _wrap(d, line, font(17, False), W - 80 - 130):   # the bar sits where the letter would
        d.text((40, y), ln, font=font(17, False), fill=col); y += 27
    d.text((40, 250), f"Time in the {BAND} m band while lead was doing it.",
           font=font(15, False), fill=DIM)
    if grade == "none":
        d.rounded_rectangle([W - 148, 150, W - 44, 164], 3, fill=GRADE["none"])
    else:
        gf = font(96)
        d.text((W - 48 - d.textlength(grade, font=gf), 92), grade, font=gf, fill=GRADE[grade])
    return im


def rejoin_card(grade):
    im, d = _frame(GRADE[grade])
    _head(d, "CHECK RIDE — GRADESHEET")
    d.text((40, 94), "REJOIN", font=font(30), fill=INK)
    line, col = rejoin_line(grade)
    d.text((40, 160), line, font=font(17, False), fill=col)
    d.text((40, 250), "Pitchout to back in the band.", font=font(15, False), fill=DIM)
    gf = font(96)
    d.text((W - 48 - d.textlength(grade, font=gf), 92), grade, font=gf, fill=GRADE[grade])
    return im


def crit_card(k):
    title, why = CRIT[k]
    im, d = _frame(GRADE["U"], crit=True)
    _head(d, "CHECK RIDE — CRITICAL ITEM")
    d.text((40, 100), title.upper(), font=_fit(d, title.upper(), W - 80, start=34, floor=22), fill=GRADE["U"])
    d.text((40, 156), why, font=font(18, False), fill=INK)
    d.text((40, 250), "A critical item is a U regardless of the items above.",
           font=font(15, False), fill=DIM)
    return im


def overall_card(k):
    letter, title, why, tone = OVERALL[k]
    im, d = _frame(GRADE[tone])
    _head(d, "CHECK RIDE — OVERALL")
    gf = font(96)
    d.text((44, 92), letter, font=gf, fill=GRADE[tone])
    x = 60 + int(d.textlength(letter, font=gf))
    y = 96
    for ln in _wrap(d, title.upper(), font(24), W - x - 40):
        d.text((x, y), ln, font=font(24), fill=INK); y += 32
    y += 14
    for ln in _wrap(d, why, font(16, False), W - x - 40):
        d.text((x, y), ln, font=font(16, False), fill=DIM); y += 25
    return im


def build() -> list[Path]:
    OUT.mkdir(parents=True, exist_ok=True)
    cards = {}
    for item in CK.ITEMS:
        for g in ("E", "G", "F", "U", "none"):
            cards[f"{item}_{g}"] = item_card(CK.ITEM_LABEL[item], g)
    for g in ("E", "G", "F", "U"):
        cards[f"rejoin_{g}"] = rejoin_card(g)
    for k in (1, 2, 3):
        cards[f"crit_{k}"] = crit_card(k)
    for k in OVERALL:
        cards[f"overall_{k}"] = overall_card(k)
    assert len(cards) == 26, len(cards)
    written = []
    for stem, im in cards.items():
        p = OUT / f"checkride_{stem}.png"
        # palette-quantised, as the shipped art was: a quarter of the bytes in
        # every graded .miz, and DCS reads 8-bit PNG with alpha fine.
        im.quantize(colors=64, method=Image.Quantize.FASTOCTREE).save(p, optimize=True)
        written.append(p)
    return written


if __name__ == "__main__":
    ps = build()
    print(f"wrote {len(ps)} cards to {OUT}")
