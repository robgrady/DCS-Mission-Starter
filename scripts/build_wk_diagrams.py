#!/usr/bin/env python3
"""Extract the attack diagrams from the 70 TFS Conventional Tactics guide.

WHY THE DIAGRAMS AND NOT A REDRAW
---------------------------------
A pilot in the pop needs a PICTURE, and the squadron already drew the right
one. Redrawing it would mean re-deriving every angle by eye from a scan and
producing a second source of truth for geometry we cannot check — the exact
mistake the honest-numbers rule exists to stop. So the diagram on the kneeboard
is the squadron's diagram.

WHAT THIS DOES
--------------
Rasterises five pages of the source PDF, thresholds the scan to clean line art,
crops to the ink, and writes kneeboard-ready PNGs into missiongen/data/wk/.
Deterministic: same PDF in, same bytes out.

    python3 scripts/build_wk_diagrams.py <path-to-70th_TFS_Conventional_Tactics.pdf>

The outputs are COMMITTED, because the source PDF is not in the repository —
it is a personal copy of a 1980 squadron document. Anyone rebuilding needs
their own copy.

PROVENANCE, WHICH IS A REAL QUESTION AND NOT A FOOTNOTE
-------------------------------------------------------
The source is marked FOR OFFICIAL USE ONLY and dated 1980. FOUO is a handling
caveat rather than a classification, and works of the US federal government are
generally not subject to copyright. Citing the numbers and reproducing the
ARTWORK are nonetheless different questions, and the guide says so on the page
that carries them.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "missiongen" / "data" / "wk"

# page number in the PDF -> asset key. The page numbers are 1-based, as
# pdftoppm counts them.
PAGES = {
    8: "split_lowhigh",
    9: "split_lowlow",
    12: "bnai",
    14: "echelon",
    18: "double90",
}

INK = 150          # anything darker than this is ink, not scanner gray
EDGE_TRIM = 60     # px of scan edge to ignore: punch holes and page shadow
PAD = 26           # white margin left around the cropped diagram
MAX_W, MAX_H = 940, 1120   # fits inside a 1024x1366 kneeboard page frame


def _drop_punch_holes(mask: np.ndarray) -> np.ndarray:
    """Erase the binder punch holes without touching the drawing.

    CALIBRATED, NOT GUESSED. The first attempt used fill ratio alone with a
    wide size window, and it ate the type: "DOUBLE 90" came out "OU LE O",
    "TRACK POINT" as "TR CK POINT". Bold sans capitals — A, D, B, M, N — are
    solid enough to pass a fill test.

    Measured on the source scans at 200 dpi, the two populations do not
    overlap at all:

        punch holes   54-62 wide, 75-77 tall, fill 0.71-0.75, at x < 4% of width
        type          13-19 wide, 12-23 tall

    So SIZE is the discriminator and fill is only a confirmation. Position is
    required as well: a hole is in the binder margin by definition, and
    anything that size in the middle of the page is part of the drawing.
    """
    from scipy import ndimage
    W = mask.shape[1]
    lab, _n = ndimage.label(mask)
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        h = sl[0].stop - sl[0].start
        w = sl[1].stop - sl[1].start
        edge = sl[1].start < 0.10 * W or sl[1].stop > 0.90 * W
        if not edge:
            continue
        # A hole clipped by the page edge is a crescent — shorter than a whole
        # one but still far larger than any letter. Allow the shorter shape
        # only right against the binder margin, where nothing else lives.
        min_h = 32 if sl[1].start < 0.05 * W else 50
        if not (30 <= w <= 110 and min_h <= h <= 130):
            continue
        blob = (lab[sl] == i)
        if blob.sum() / float(w * h) > 0.60:
            mask[sl][blob] = False
    return mask


def _clean(png: Path) -> Image.Image:
    a = np.array(Image.open(png).convert("L"))
    # Drop the scan edges before looking for ink. Binder punch holes are solid
    # black discs and would otherwise dominate the bounding box, cropping the
    # page to a hole instead of to the drawing.
    inner = a[EDGE_TRIM:-EDGE_TRIM, EDGE_TRIM:-EDGE_TRIM]
    mask = _drop_punch_holes(inner < INK)
    # write the holes back out to paper before anything else measures the page
    inner[~mask] = 255
    a[EDGE_TRIM:-EDGE_TRIM, EDGE_TRIM:-EDGE_TRIM] = inner
    # Ignore rows/columns with only a trace of ink: speckle, not line work.
    rows = np.where(mask.sum(axis=1) > 3)[0]
    cols = np.where(mask.sum(axis=0) > 3)[0]
    if not len(rows) or not len(cols):
        raise SystemExit(f"{png.name}: no ink found")
    y0, y1 = rows[0] + EDGE_TRIM, rows[-1] + EDGE_TRIM
    x0, x1 = cols[0] + EDGE_TRIM, cols[-1] + EDGE_TRIM
    crop = a[max(0, y0 - PAD):y1 + PAD, max(0, x0 - PAD):x1 + PAD]
    # Flatten the scan: paper to white, ink to black, nothing in between. The
    # kneeboard renders on a paper background and a gray halo reads as smudge.
    out = np.where(crop < INK, 0, 255).astype("uint8")
    img = Image.fromarray(out, "L")
    img.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
    return img


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    pdf = Path(sys.argv[1]).expanduser()
    if not pdf.is_file():
        raise SystemExit(f"not a file: {pdf}")
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for page, key in sorted(PAGES.items()):
            subprocess.run(["pdftoppm", "-r", "200", "-f", str(page),
                            "-l", str(page), "-png", str(pdf),
                            str(Path(td) / f"p{page}")], check=True)
            src = next(Path(td).glob(f"p{page}-*.png"))
            img = _clean(src)
            dest = OUT / f"wk_{key}.png"
            img.save(dest, "PNG", optimize=True)
            print(f"  {dest.relative_to(ROOT)}  {img.size[0]}x{img.size[1]}  "
                  f"{dest.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
