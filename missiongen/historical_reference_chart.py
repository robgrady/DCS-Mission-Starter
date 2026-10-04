"""Dated point diagrams: never connect schematic references into invented routes."""
from html import escape
import math
from .historical_library import profile


def render_svg(profile_id, view='overview'):
    data = profile(profile_id)
    if view not in ('overview', 'local') or view == 'local' and profile_id != 'nevada-1981':
        raise ValueError('Unknown historical chart view')
    points = data['points']
    if view == 'local':
        bounds = (36.08, 36.80, -115.25, -114.48)
    else:
        lats = [p['latitude_decimal_degrees'] for p in points]
        lons = [p['longitude_decimal_degrees'] for p in points]
        bounds = (min(lats)-.10, max(lats)+.10, min(lons)-.12, max(lons)+.12)
    south, north, west, east = bounds
    x0, y0, width, height = 75, 60, 805, 420
    def xy(lat, lon):
        return x0+(lon-west)/(east-west)*width, y0+(north-lat)/(north-south)*height
    esc = escape
    rows = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 555" role="img" aria-labelledby="chart-title-{profile_id}-{view} chart-desc-{profile_id}-{view}">',
            f'<title id="chart-title-{profile_id}-{view}">{esc(data["label"])}: {view} point reference</title>',
            f'<desc id="chart-desc-{profile_id}-{view}">{esc(data["plotting_note"])}</desc>',
            '<rect width="960" height="555" fill="#fff"/>',
            '<g font-family="Source Sans 3, sans-serif" fill="#101828">',
            f'<text x="75" y="25" font-size="21" font-weight="700">{esc(data["label"])} - {view} reference</text>',
            '<text x="75" y="45" font-size="13">Printed coordinates; datum unverified. No route or boundary inferred.</text>']
    step = .25 if view == 'local' else .5
    for n in range(math.ceil(south/step), math.floor(north/step)+1):
        lat = n*step; _, y = xy(lat, west)
        rows += [f'<path d="M75 {y:.2f}H880" stroke="#D0D5DD"/>',
                 f'<text x="65" y="{y+4:.2f}" text-anchor="end" font-size="12">{lat:.2f} N</text>']
    for n in range(math.ceil(west/step), math.floor(east/step)+1):
        lon = n*step; x, _ = xy(south, lon)
        rows += [f'<path d="M{x:.2f} 60V480" stroke="#D0D5DD"/>',
                 f'<text x="{x:.2f}" y="499" text-anchor="middle" font-size="12">{abs(lon):.2f} W</text>']
    used = []
    for i, point in enumerate(points, 1):
        lat, lon = point['latitude_decimal_degrees'], point['longitude_decimal_degrees']
        if not south <= lat <= north or not west <= lon <= east:
            continue
        x, y = xy(lat, lon)
        name = esc(f"{i}. {point['name']}: {point['coordinate_raw']['north_lat']} N, {point['coordinate_raw']['west_lon']} W; datum unverified")
        rows.append(f'<g class="reference-point" data-point="{esc(point["id"])}" tabindex="0" role="button" aria-label="{name}"><title>{name}</title>')
        if point.get('kind') == 'navaid':
            rows.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="#fff" stroke="#00205B" stroke-width="2"/>')
        else:
            rows.append(f'<path d="M{x:.2f} {y-6:.2f}l6 6 -6 6 -6 -6Z" fill="#fff" stroke="#1D4E89" stroke-width="2"/>')
        lx, ly = x+9, y-9
        for dx, dy in [(9,-9),(9,16),(-25,-9),(-25,16),(9,-28),(-25,-28),(26,0),(-42,0)]:
            px, py = x+dx, y+dy
            if x0 <= px <= 858 and y0+12 <= py <= 477 and all(abs(px-a)>22 or abs(py-b)>15 for a,b in used):
                lx, ly = px, py; break
        used.append((lx,ly))
        rows.append(f'<path d="M{x:.2f} {y:.2f}L{lx:.2f} {ly-4:.2f}" stroke="#D0D5DD"/><text x="{lx:.2f}" y="{ly:.2f}" font-size="13" font-weight="700">{i}</text></g>')
    rows += ['<text x="75" y="531" font-size="13">Diamond: published point | Circle: navaid | Numbers match the coordinate table.</text>', '</g></svg>']
    return ''.join(rows)
