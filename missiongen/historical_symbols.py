"""Reference-chart symbols. Shape and labels carry meaning without color."""
from dcs import mapping
from dcs.drawing.drawing import LineStyle

from . import chartstyle as cs


LEGEND = [
    'HISTORICAL REFERENCES — not operational clearance',
    'DOC = documented structure; ~ = reconstructed geometry',
    'Dashed lane = reconstructed route; blocks/widths are planning values',
    'Diamond = reporting gate; circle = control/reference zone',
    'Hatched boundary = restricted/exclusion area; dash-dot = deconfliction',
    'Dotted shape / TRAINING = illustrative; arrow / AXIS = threat direction',
    'REF date = source/event date, not continuous validity; DATE ? = unknown',
]


def style(depiction, selected=True):
    """Preserve the established palette; never encode confidence by hue alone."""
    category = {'formal_corridor':'corridor', 'control_zone':'zone',
                'restricted_area':'restricted', 'deconfliction_line':'deconfliction',
                'illustrative_zone':'restricted', 'training_axis':'deconfliction',
                'reconstructed_lane':'corridor', 'reported_route':'corridor'}[depiction]
    color, fill, weight, line = cs.spec(category)
    if depiction in ('reconstructed_lane', 'reported_route'):
        line = LineStyle.Dash
        fill = cs._fill(color, 0)
    elif depiction == 'illustrative_zone':
        line = LineStyle.Dot
        fill = cs._fill(color, 0)
    elif depiction == 'deconfliction_line':
        line = LineStyle.DotDash
    return color, fill, weight if selected else 1, line


def diamond(layer, point, radius=1852.0, approximate=False):
    from .airspace import _draw_poly
    points = [mapping.Point(point.x+dx, point.y+dy, point._terrain)
              for dx,dy in ((radius,0),(0,radius),(-radius,0),(0,-radius))]
    color, fill, _, _ = cs.spec('zone')
    _draw_poly(layer, points, color, cs._fill(color,0), 2,
               LineStyle.Dash if approximate else LineStyle.Solid)


def label_tag(entry):
    from .historical_coverage import visual_tag
    prefix = '' if entry['geometry_accuracy'] in ('sourced_center_and_radius', 'sourced_1995_polygon') else '~ '
    period = 'REF '+entry['reference_date'] if entry['reference_date'] else 'DATE ?'
    return prefix + visual_tag(entry) + ' | ' + period


def legend(m, anchor=None):
    """One compact key per mission, offset from home instead of over a route."""
    layer = m.drawings.get_layer_by_name('Common')
    if any(getattr(o,'text','').startswith(LEGEND[0]) for o in layer.objects):
        return
    if anchor is None:
        airports = list(m.terrain.airports.values())
        if not airports:
            return
        anchor = airports[0].position
    point = mapping.Point(anchor.x-24000,anchor.y-24000,m.terrain)
    cs.label(layer,point,'\n'.join(LEGEND),cs.WHITE,size=11)


def circle_points(center, radius_m, vertices=96):
    """Geodesic circles preserve large published radii across terrain projection."""
    from pyproj import Geod
    from dcs.mapping import LatLng
    ll=center.latlng();geod=Geod(ellps='WGS84');points=[]
    for i in range(vertices):
        lon,lat,_=geod.fwd(ll.lng,ll.lat,i*360/vertices,radius_m)
        points.append(mapping.Point.from_latlng(LatLng(lat,lon),center._terrain))
    return points


def boundary_ticks(layer, points, spacing=18000.0, length=3500.0):
    """Inward hatch marks distinguish an exclusion boundary at F10 scale."""
    import math
    from .airspace import _draw_line
    center_x = sum(p.x for p in points)/len(points)
    center_y = sum(p.y for p in points)/len(points)
    color, _, _, _ = cs.spec('restricted')
    for a, b in zip(points, points[1:]+points[:1]):
        dx, dy = b.x-a.x, b.y-a.y
        distance = math.hypot(dx, dy)
        if not distance:
            continue
        nx, ny = -dy/distance, dx/distance
        mx, my = (a.x+b.x)/2, (a.y+b.y)/2
        if (center_x-mx)*nx+(center_y-my)*ny < 0:
            nx, ny = -nx, -ny
        count = max(1, int(distance/spacing))
        for i in range(count):
            t = (i+0.5)/count
            p = mapping.Point(a.x+t*dx,a.y+t*dy,a._terrain)
            end = mapping.Point(p.x+nx*length,p.y+ny*length,p._terrain)
            _draw_line(layer,[p,end],color,1,LineStyle.Solid)
