#!/usr/bin/env python3
"""Render the six coached-B'NAI brief pages.

IDEMPOTENT.

SAME VISUAL LANGUAGE AS THE CUE CARDS, DIFFERENT JOB. A cue card is glanced at
in a pop: one word, enormous, on a cropped drawing. A brief page is READ,
sitting still, with the controls locked — so it is a page of type at a size
somebody can actually read, with the drawing above it where there is a drawing
to show.

THREE PAGES CARRY THE SQUADRON'S DRAWING and three do not, because we do not
have a picture of Cairo West in 1980 and inventing one would be the same
mistake as redrawing the geometry. A page with no photograph is a page with no
photograph; it says its piece in type.

Usage:  PYTHONPATH=.:vendor python3 scripts/build_wk_brief_pages.py
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor"))

from PIL import Image, ImageDraw, ImageFont          # noqa: E402

from missiongen import wk, wk_brief                  # noqa: E402

import importlib.util                                # noqa: E402
_spec = importlib.util.spec_from_file_location(
    "bwcc", ROOT / "scripts" / "build_wk_coach_cards.py")
CARDS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CARDS)

FONTS = ROOT / "missiongen" / "data" / "brand" / "fonts"
OUT = ROOT / "missiongen" / "data" / "wk_brief"

W, H = 1180, 900
MARGIN = 52
INK = (17, 17, 17)
RED = (200, 24, 24)
PAPER = (255, 255, 255)
RULE = (170, 170, 170)

# WIDER CROPS THAN THE CUE CARDS USE, and the reason is the reading distance.
# A cue card is glanced at, so it is cropped tight to the geometry and the
# labels can lose a letter off the left edge without costing anything. A brief
# page is read, and "TRACK POINT" rendered as "OINT" reads as a broken file.
#
# x starts at 12 rather than 0: the binder punch holes on this scan occupy
# x 0-5 (measured, at y 66-103 and y 563-594) and the leftmost label ink
# starts at x 28. Twelve clears one and keeps the other.
PANEL_ATTACK = (12, 95, 846, 655)
# Both egress figures, not one — the page's own text is about choosing between
# egress heading and line abreast, and the drawing shows both options.
PANEL_EGRESS = (10, 748, 846, 1118)

# Which panel of the squadron's page each illustrated brief page shows, and
# which points get ringed. `None` means a type-only page.
PICTURES = {
    "attack": (PANEL_ATTACK, ["split"]),
    # All four pop stages at once — this is the page that teaches the SHAPE,
    # so it shows the whole climb rather than one moment of it.
    "pop": (PANEL_ATTACK, ["pup", "rollin", "apex", "track"]),
    "egress": (PANEL_EGRESS, ["egress"]),
}


def _font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def _wrap(draw, text, font, width):
    out = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        for w in words:
            t = (cur + " " + w).strip()
            if draw.textlength(t, font=font) <= width:
                cur = t
            else:
                out.append(cur)
                cur = w
        out.append(cur)
    return out


def _drawing(pic_key):
    panel, marks = PICTURES[pic_key]
    src = Image.open(CARDS.SRC).convert("RGB")
    d = ImageDraw.Draw(src)
    for box in CARDS.WHITEOUT:
        d.rectangle(box, fill=PAPER)
    r = CARDS.RING_R
    for name in marks:
        (mx, my), _p = CARDS.MARKS[name]
        d.ellipse([mx - r, my - r, mx + r, my + r], outline=RED, width=6)
    return src.crop(panel)


def build_page(i, key, head, pic_key, text, total):
    card = Image.new("RGB", (W, H), PAPER)
    dr = ImageDraw.Draw(card)

    f_head = _font("BarlowCondensed-ExtraBold.ttf", 66)
    f_num = _font("IBMPlexMono-Medium.ttf", 22)
    f_body = _font("SourceSans3-VF.ttf", 30)
    f_foot = _font("IBMPlexMono-Medium.ttf", 21)

    dr.text((MARGIN, 34), f"{i + 1} / {total}", font=f_num, fill=RED)
    sq = f"{wk.SQUADRON} · {wk.NICKNAME}"
    dr.text((W - MARGIN - dr.textlength(sq, font=f_num), 36), sq,
            font=f_num, fill=(120, 120, 120))
    dr.text((MARGIN, 62), head, font=f_head, fill=INK)
    y = 62 + f_head.size + 16
    dr.line([MARGIN, y, W - MARGIN, y], fill=INK, width=3)
    y += 26

    if pic_key:
        im = _drawing(pic_key)
        room_w, room_h = W - 2 * MARGIN, 372
        k = min(room_w / im.width, room_h / im.height)
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        card.paste(im, ((W - im.width) // 2, y))
        y += im.height + 22

    body_w = W - 2 * MARGIN
    lines = _wrap(dr, text, f_body, body_w)
    # Shrink the body rather than let it run off the page. A brief that clips
    # its own last sentence is worse than a small one.
    while y + len(lines) * (f_body.size + 11) > H - 78 and f_body.size > 17:
        f_body = _font("SourceSans3-VF.ttf", f_body.size - 1)
        lines = _wrap(dr, text, f_body, body_w)
    for ln in lines:
        dr.text((MARGIN, y), ln, font=f_body, fill=INK)
        y += f_body.size + 11

    foot = ("SPACE  continue" if i == 0
            else "SPACE  continue     BACKSPACE  back")
    if i + 1 == total:
        foot = "SPACE  take the airplane"
    dr.line([MARGIN, H - 60, W - MARGIN, H - 60], fill=RULE, width=2)
    dr.text((MARGIN, H - 46), foot, font=f_foot, fill=INK)

    out = OUT / f"wk_brief_{key}.png"
    OUT.mkdir(parents=True, exist_ok=True)
    card.save(out, optimize=True)
    return out


def build_clear():
    """A blank page, for taking the brief OFF the screen.

    THERE IS NO ACTION THAT REMOVES A PICTURE. `PictureToGroup` is the only
    lever DCS gives a mission file, and its `clearview` flag REPLACES whatever
    is showing — so the only way to stop showing something is to show something
    else. This is that something else: fully transparent, displayed for one
    second, which reads in the cockpit as the brief simply going away.

    Rob found the bug by flying it: the last page is drawn for ten minutes and
    nothing ever replaced it, so pressing SPACE handed back the controls, armed
    the coaching, and left the brief sitting over the canopy.
    """
    im = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    out = OUT / "wk_brief_clear.png"
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return out


def main():
    pg = wk_brief.pages()
    for i, (key, head, pic, text) in enumerate(pg):
        p = build_page(i, key, head, pic, text, len(pg))
        print(f"  {p.relative_to(ROOT)}  {head}")
    c = build_clear()
    print(f"  {c.relative_to(ROOT)}  (blank, to clear the last page)")
    print(f"{len(pg)} brief pages")


if __name__ == "__main__":
    main()
