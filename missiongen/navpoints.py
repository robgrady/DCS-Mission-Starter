"""BB-22: named geographic reference points — the landmarks crews navigate by
(Belted Peak, Student Gap, Coyote Summit...). Marked on the F10 map via the
Common drawing layer, added as trigger zones for mission logic, listed in the
briefing, and plotted on the kneeboard theater page."""
from dcs import mapping
from dcs.mapping import LatLng
from dcs.drawing.drawing import Rgba

from .resolver import load_json

MARK = Rgba(255, 215, 80, 255)       # gold text/ring
FILL = Rgba(255, 215, 80, 25)

TYPE_TAG = {"peak": "▲", "corridor": "»", "lake": "◍", "landmark": "●"}


def add_nav_points(m, map_key):
    """Returns [(name, point, type, note)] and draws them on the F10 map."""
    data = load_json("nav_points").get(map_key, [])
    if not data:
        return []
    layer = m.drawings.get_layer_by_name("Common")
    out = []
    for np in data:
        pos = mapping.Point.from_latlng(LatLng(np["lat"], np["lon"]), m.terrain)
        tag = TYPE_TAG.get(np["type"], "●")
        label = f"{tag} {np['name']}"
        layer.add_text_box(pos, label, color=MARK, fill=Rgba(0, 0, 0, 90),
                           font_size=14, border_thickness=0)
        layer.add_circle(pos, radius=1200, color=MARK, fill=FILL,
                         line_thickness=2)
        m.triggers.add_triggerzone(pos, radius=1500, name=f"NAV {np['name']}")
        out.append((np["name"], pos, np["type"], np.get("note", "")))
    return out


def briefing_block(points):
    if not points:
        return ""
    lines = ["", "== NAV REFERENCE POINTS =="]
    for name, pos, ptype, note in points:
        ll = pos.latlng()
        lines.append(f"{name:<28} {ll.lat:8.4f} {ll.lng:9.4f}  {note}")
    return "\n".join(lines)
