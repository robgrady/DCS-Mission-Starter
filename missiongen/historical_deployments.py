"""Map symbols for dated unit observations anchored to DCS airfields."""

from dcs import mapping

from . import chartstyle
from .historical_library import deployment_snapshots


def add_deployment_references(mission, map_key):
    """Draw the observed bases for the mission date and return IDs and brief lines."""
    day = mission.start_time.date().isoformat()
    by_airfield = {}
    for row in deployment_snapshots(map_key, day):
        by_airfield.setdefault(row["map_airport"], []).append(row)
    if not by_airfield:
        return [], []

    layer = mission.drawings.get_layer_by_name("Common")
    drawn = []
    lines = []
    color = chartstyle.WHITE
    for airport_key, rows in by_airfield.items():
        airport = mission.terrain.airports.get(airport_key)
        if airport is None:
            continue

        base = rows[0]["base"]
        assignments = []
        for row in rows:
            unit = row["unit"].replace("Expeditionary Fighter Squadron", "EFS")
            aircraft = row.get("aircraft_variants") or row.get("aircraft_families") or []
            assignments.append(f"{unit} | {', '.join(aircraft)}" if aircraft else unit)
            drawn.append(row["id"])

        point = airport.position
        square = layer.add_rectangle(point, width=1200, height=1200,
                                     color=color, fill=chartstyle._fill(color, 0),
                                     line_thickness=2)
        square.name = f"Historical deployment: {base}"
        label_point = mapping.Point(point.x + 900, point.y + 900, mission.terrain)
        chartstyle.label(layer, label_point, "\n".join([f"{base} | ARCHIVE {day}", *assignments]),
                         color, size=12)
        lines.append(f"{base}: {'; '.join(assignments)}")

    if not drawn:
        return [], []
    return drawn, [
        "",
        f"== ARCHIVAL AIRFIELD OBSERVATIONS | {day} ==",
        "Open squares on F10 mark DCS airfield reference points. "
        "The observations record dated unit presence at those bases.",
        *lines,
        "See the Historical Library for sources and limits.",
    ]
