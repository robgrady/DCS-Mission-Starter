#!/usr/bin/env python3
"""Build the AAR position-indicator art that ships inside every graded .miz.

REDRAWN FOR 10% OF THE WINDOW, from cockpit feedback. The first version was a
420x300 card with three lines of prose, shown at 22%. At half that size the
prose is unreadable and the card is still large enough to compete with the
tanker — so this is not the old art scaled down, it is different art.

WHAT CHANGED AND WHY:

  * TALL AND NARROW (200x360), because it now lives on the LEFT edge at eye
    level rather than under the nose, and a wide card there eats the canopy.
  * THE VERTICAL AXIS IS A BALL BETWEEN DATUMS — the meatball, deliberately.
    A naval aviator already knows how to read "the light is above the green
    line" at a glance, and borrowing a sight picture somebody already owns is
    cheaper than teaching a new one.
  * FORE/AFT IS ONE BIG CHEVRON, top or bottom, not a pair either side.
  * AT MOST ONE WORD. At 10% of a 2560-wide window this renders about 256 px
    tall; anything longer than a single word is decoration.

Deterministic: same code, same bytes, so a mission built twice is identical.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).parent.parent / "missiongen" / "data" / "hud"
SHEET = Path(__file__).parent.parent / "docs" / "img"
W, H = 200, 360

BG = (10, 12, 16, 226)
EDGE = (108, 120, 138, 255)
GOOD = (74, 222, 112, 255)
WARN = (255, 190, 66, 255)
BAD = (255, 92, 82, 255)
DATUM = (150, 160, 178, 255)
INK = (240, 244, 250, 255)


def font(sz, bold=True):
    p = "/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else "")
    try:
        return ImageFont.truetype(p, sz)
    except OSError:
        return ImageFont.load_default()


def _frame():
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, W - 3, H - 3], 12, fill=BG, outline=EDGE, width=2)
    return im, d


def card(fore, vert):
    """fore: -1 falling back, 0 on speed, +1 closing. vert: -1 low, 0 on, +1 high."""
    im, d = _frame()
    cx, cy = W // 2, 176

    # THREE ZONES that must not overlap, or the ball at an extreme merges into
    # the chevron and the card reads as one shapeless blob. The first cut of
    # this art did exactly that.
    #   top strip     y  38-100   closing chevron
    #   ball travel   y 106-246   (cy 176, +/-46, radius 24)
    #   bottom strip  y 252-314   falling-back chevron
    ball_r, ball_travel = 24, 46

    # datum bars — the reference the ball is read against, always drawn
    for x0, x1 in ((14, 58), (W - 58, W - 14)):
        d.rounded_rectangle([x0, cy - 5, x1, cy + 5], 3, fill=DATUM)

    col = GOOD if (fore == 0 and vert == 0) else (
        WARN if abs(fore) + abs(vert) == 1 else BAD)

    off = {1: -ball_travel, 0: 0, -1: ball_travel}[vert]
    d.ellipse([cx - ball_r, cy + off - ball_r,
               cx + ball_r, cy + off + ball_r], fill=col)
    # a bar through it, so the state survives greyscale and color-blindness
    d.rounded_rectangle([cx - 13, cy + off - 4, cx + 13, cy + off + 4], 3,
                        fill=BG[:3] + (255,))

    # fore/aft: one chevron pair, top for closing, bottom for falling back
    if fore:
        up = fore > 0
        ytip, ybase = (38, 68) if up else (H - 38, H - 68)
        for k in (0, 32):
            yt = ytip + (k if up else -k)
            yb = ybase + (k if up else -k)
            d.polygon([(cx - 38, yb), (cx, yt), (cx + 38, yb)], fill=col)

    # ONE WORD, and it names the FORE/AFT state whenever there is one, because
    # that is the axis the throttle has to act on. The ball already shows high
    # and low unambiguously, so the word backs up the axis the picture is
    # weakest at rather than repeating the one it is strongest at.
    word = ("HOLD" if (fore == 0 and vert == 0) else
            ("FAST" if fore > 0 else "SLOW" if fore < 0 else
             "HIGH" if vert > 0 else "LOW"))
    d.text((cx, H - 24), word, font=font(28), fill=col, anchor="mm")
    return im


def out_of_position():
    im, d = _frame()
    cx = W // 2
    d.rounded_rectangle([2, 2, W - 3, H - 3], 12, fill=(24, 16, 16, 232),
                        outline=DATUM, width=2)
    d.ellipse([cx - 46, 118, cx + 46, 210], outline=DATUM, width=7)
    d.line([cx - 34, 130, cx + 34, 198], fill=DATUM, width=7)
    d.text((cx, H - 62), "BACK", font=font(34), fill=INK, anchor="mm")
    d.text((cx, H - 26), "OUT", font=font(30), fill=DATUM, anchor="mm")
    return im


def breakoff():
    """The safety state, and the only one allowed to shout. More than 25 kt of
    overtake inside a quarter mile is somebody else's problem as well."""
    im, d = _frame()
    d.rounded_rectangle([2, 2, W - 3, H - 3], 12, fill=(46, 12, 12, 240),
                        outline=BAD, width=4)
    cx = W // 2
    for k in (0, 30, 60):
        d.polygon([(cx - 52, 128 + k), (cx, 78 + k), (cx + 52, 128 + k)],
                  fill=BAD)
    d.text((cx, H - 66), "POWER", font=font(30), fill=BAD, anchor="mm")
    d.text((cx, H - 28), "OFF", font=font(40), fill=INK, anchor="mm")
    return im


def _save(im, path):
    """Palette-quantise. Eleven PNGs ride inside every graded mission and the
    art is flat color, so 8-bit costs nothing.

    FASTOCTREE, not MEDIANCUT: median-cut cannot quantise RGBA, and these cards
    are transparent-cornered by design so the rounded edge sits on the cockpit
    rather than on a black box."""
    bg = Image.new("RGBA", im.size, (0, 0, 0, 0))
    bg.alpha_composite(im)
    bg.quantize(colors=64, method=Image.Quantize.FASTOCTREE).save(
        path, optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    SHEET.mkdir(parents=True, exist_ok=True)
    cells = [(f, v) for v in (1, 0, -1) for f in (-1, 0, 1)]
    made = []
    for f, v in cells:
        im = card(f, v)
        _save(im, OUT / f"aar_hud_f{f}_v{v}.png")
        made.append(im)
    o, b = out_of_position(), breakoff()
    _save(o, OUT / "aar_hud_out.png")
    _save(b, OUT / "aar_hud_breakoff.png")

    pad, cols = 14, 6
    tiles = made + [o, b]
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * W + (cols + 1) * pad,
                              rows * H + (rows + 1) * pad + 44), (26, 28, 34))
    sd = ImageDraw.Draw(sheet)
    sd.text((pad, 14), "AAR indicator — left edge, eye level, 10% of window "
            "(shown at 100%)", font=font(19), fill=(232, 236, 244))
    for i, im in enumerate(tiles):
        sheet.paste(im, (pad + (i % cols) * (W + pad),
                         44 + pad + (i // cols) * (H + pad)), im)
    sheet.save(SHEET / "aar_hud_mockup.png")
    print(f"{len(tiles)} states -> {OUT}")


if __name__ == "__main__":
    main()
