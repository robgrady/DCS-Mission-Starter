"""Mission-start brand splash.

Shows a logo image full-screen for a few seconds when the mission launches, then
it clears — the same "Picture to All" trigger (DCS `a_out_picture`) that campaign
creators use for their intro logos. Purely cosmetic: no units, no waypoints, no
effect on the mission. The image ships in `data/brand/`.
"""
from pathlib import Path

from dcs.triggers import TriggerStart
from dcs.action import PictureToAll, PictureAction

_LOGO = Path(__file__).parent / "data" / "brand" / "authentic_media.png"


def add_brand_splash(m, seconds: int = 8, start_delay: int = 1, logo_path=None):
    """Add a mission-start logo splash to the mission. Returns True if added,
    False if the logo asset is missing (never raises — branding is optional)."""
    path = Path(logo_path) if logo_path else _LOGO
    if not path.exists():
        return False
    key = m.map_resource.add_resource_file(str(path))
    act = PictureToAll(
        file_res_key=key,
        seconds=int(seconds),
        clearview=False,
        start_delay=int(start_delay),
        horz_alignment=PictureAction.HorzAlignment.Center,
        vert_alignment=PictureAction.VertAlignment.Center,
        size=60,
        size_units=PictureAction.SizeUnits.WindowSize)
    # pydcs serialises the alignment/size enums as bare identifiers
    # (e.g. `HorzAlignment.Center`), which is invalid Lua — the .miz won't even
    # reload, and DCS expects the string values ("0"/"1"/"2"). Coerce to values.
    act.horz_alignment = act.horz_alignment.value
    act.vert_alignment = act.vert_alignment.value
    act.size_units = act.size_units.value
    act.params = [act.file_res_key, act.seconds, act.clearview, act.start_delay,
                  act.horz_alignment, act.vert_alignment, act.size, act.size_units]
    trig = TriggerStart(comment="Authentic Media brand splash")
    trig.actions.append(act)
    m.triggerrules.triggers.append(trig)
    return True
