"""International Alignment — Theater Identity pillar 1.

Per-map/era real national ownership of each airbase (data/theater_identity.json).
The builder uses this to dress each base with its OWNING nation's DCS country, so
statics carry the correct national identity and liveries instead of one country
per side. Additive: no entry for a base => the side's preset country; no block
for a map/era => a full no-op.
"""
from .resolver import load_json


def bases(map_key, era):
    """{ airbase_name: pydcs_country_name } for this map+era, or {}."""
    try:
        data = load_json("theater_identity")
    except Exception:
        return {}
    return data.get(map_key, {}).get(era, {}).get("bases", {})


def owner(map_key, era, base_name):
    """Owning nation (pydcs country name) for one base, or None."""
    return bases(map_key, era).get(base_name)


def roster_theme(era, nation, side_theme):
    """Theme dict for an aligned nation: its fast-jet 'planes' roster merged over
    the side theme (transports/helos inherit from the side). Returns side_theme
    unchanged when the nation has no roster for the era."""
    if not side_theme:
        return side_theme
    try:
        rosters = load_json("nation_rosters")
    except Exception:
        return side_theme
    r = rosters.get(era, {}).get(nation)
    if not r:
        return side_theme
    merged = dict(side_theme)
    for k in ("planes", "large", "helos"):
        if k in r:
            merged[k] = r[k]
    return merged
