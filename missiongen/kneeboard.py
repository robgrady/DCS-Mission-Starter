"""BB-19: kneeboard nav charts — rendered server-side, injected into the .miz.

DCS loads mission kneeboard pages from KNEEBOARD/IMAGES/ inside the .miz.
Pages (3:4 portrait, 1024x1366):
  01 comms/nav card          02 airfield data           03 theater overview
No player waypoints anywhere — charts are reference, not routing (boundary principle).
"""
import io
import zipfile
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1366
BG = (24, 28, 34)
FG = (222, 230, 238)
DIM = (140, 150, 160)
ACCENT = (110, 168, 254)
BLUE = (90, 150, 250)
RED = (235, 90, 80)
LINE = (60, 70, 82)

_F = "/usr/share/fonts/truetype/dejavu/"


def _fonts():
    try:
        return {
            "h1": ImageFont.truetype(_F + "DejaVuSans-Bold.ttf", 44),
            "h2": ImageFont.truetype(_F + "DejaVuSans-Bold.ttf", 30),
            "mono": ImageFont.truetype(_F + "DejaVuSansMono.ttf", 26),
            "mono_b": ImageFont.truetype(_F + "DejaVuSansMono-Bold.ttf", 26),
            "small": ImageFont.truetype(_F + "DejaVuSans.ttf", 20),
        }
    except OSError:
        f = ImageFont.load_default()
        return {k: f for k in ("h1", "h2", "mono", "mono_b", "small")}


def _page(title, subtitle):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f = _fonts()
    d.rectangle([0, 0, W, 108], fill=(16, 20, 26))
    d.text((40, 22), title, font=f["h1"], fill=FG)
    d.text((40, 74), subtitle, font=f["small"], fill=DIM)
    d.line([0, 108, W, 108], fill=ACCENT, width=3)
    return img, d, f


def page_comms(comms, map_label, era_label, home_name, qnh_hpa=None):
    img, d, f = _page("COMMS / NAV", f"{map_label}  ·  {era_label}  ·  home: {home_name}")
    y = 150
    if qnh_hpa:
        from .pressure import format_qnh
        d.text((40, y), f"ALTIMETER (QNH)  {format_qnh(qnh_hpa)}",
               font=f["mono_b"], fill=ACCENT)
        y += 50
    has_ch = bool(getattr(comms, "channels", None))
    ch_hdr = f"{'CHAN':<6}" if has_ch else ""
    d.text((40, y), f"{'AGENCY':<14}{'C/S':<14}{'FREQ':<10}{ch_hdr}{'TACAN'}",
           font=f["mono_b"], fill=ACCENT)
    y += 44
    for agency, cs, freq, tacan, notes in comms.entries:
        ch = f"{comms.chan_label(agency):<6}" if has_ch else ""
        d.text((40, y), f"{agency:<14}{cs:<14}{freq:<10}{ch}{tacan}", font=f["mono"], fill=FG)
        if notes:
            d.text((60, y + 30), notes, font=f["small"], fill=DIM)
            y += 30
        y += 46
        d.line([40, y - 8, W - 40, y - 8], fill=LINE, width=1)
    d.text((40, H - 60), "DCS MISSION STARTER — no waypoints placed; you own the flight plan",
           font=f["small"], fill=DIM)
    return img


def page_airfields(own_fields, enemy_fields, era_year):
    img, d, f = _page("AIRFIELD DATA", f"friendly and known enemy fields · circa {era_year}")
    y = 150
    for label, fields, color in (("FRIENDLY", own_fields, BLUE), ("ENEMY (KNOWN)", enemy_fields, RED)):
        d.text((40, y), label, font=f["h2"], fill=color)
        y += 52
        d.text((40, y), f"{'FIELD':<22}{'RWY':<8}{'STANDS'}", font=f["mono_b"], fill=ACCENT)
        y += 40
        for ap in fields:
            rwys = "/".join(f"{int(round(r.heading/10)):02d}" for r in ap.runways) or "-"
            d.text((40, y), f"{ap.name[:21]:<22}{rwys:<8}{len(ap.parking_slots)}",
                   font=f["mono"], fill=FG)
            y += 40
        y += 30
    return img


def page_theater(own_fields, enemy_fields, bullseye, map_label, support_names,
                 nav_points=None):
    img, d, f = _page("THEATER OVERVIEW", f"{map_label} · schematic, not to scale for nav")
    nav_points = nav_points or []
    pts = [(a.position.x, a.position.y) for a in own_fields + enemy_fields] + [
        (bullseye["x"], bullseye["y"])] + [(p.x, p.y) for _n, p in nav_points]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    pad = max((max(xs) - min(xs)), (max(ys) - min(ys)), 1) * 0.18
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad

    def px(x, y):
        # DCS: x = north, y = east  ->  screen: east right, north up
        sx = 60 + (y - y0) / (y1 - y0) * (W - 120)
        sy = 160 + (1 - (x - x0) / (x1 - x0)) * (H - 320)
        return sx, sy

    # nav reference points: gold triangles, drawn first so airfields sit on top
    GOLD = (240, 200, 90)
    for name, p in nav_points:
        sx, sy = px(p.x, p.y)
        d.polygon([(sx, sy - 8), (sx - 7, sy + 6), (sx + 7, sy + 6)], outline=GOLD, width=2)
        d.text((sx + 10, sy - 8), name.split("/")[0].strip()[:16], font=f["small"], fill=GOLD)

    for ap, color in [(a, BLUE) for a in own_fields] + [(a, RED) for a in enemy_fields]:
        sx, sy = px(ap.position.x, ap.position.y)
        d.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], outline=color, width=4)
        d.text((sx + 16, sy - 12), ap.name[:18], font=f["small"], fill=FG)
    bx, by = px(bullseye["x"], bullseye["y"])
    for r in (18, 10):
        d.ellipse([bx - r, by - r, bx + r, by + r], outline=(240, 200, 90), width=3)
    d.text((bx + 24, by - 12), "BULLSEYE", font=f["small"], fill=(240, 200, 90))
    d.text((40, H - 90), "N ↑   " + (" · ".join(support_names) if support_names else ""),
           font=f["small"], fill=DIM)
    d.text((40, H - 60), "Support orbits behind friendly lines — freqs on COMMS page",
           font=f["small"], fill=DIM)
    return img


def inject_kneeboard(miz_path, pages):
    """Append rendered pages into the saved .miz under KNEEBOARD/IMAGES/."""
    with zipfile.ZipFile(miz_path, "a", zipfile.ZIP_DEFLATED) as z:
        for i, img in enumerate(pages, 1):
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            z.writestr(f"KNEEBOARD/IMAGES/{i:02d}_starter.png", buf.getvalue())


def build_kneeboard(miz_path, comms, own_fields, enemy_fields, bullseye,
                    map_label, era_label, era_year, home_name, support_names,
                    nav_points=None, qnh_hpa=None):
    pages = [
        page_comms(comms, map_label, era_label, home_name, qnh_hpa),
        page_airfields(own_fields, enemy_fields, era_year),
        page_theater(own_fields, enemy_fields, bullseye, map_label, support_names,
                     nav_points),
    ]
    inject_kneeboard(miz_path, pages)
    return len(pages)
