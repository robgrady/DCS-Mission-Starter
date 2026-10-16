"""Project-owned coordinate envelope; never mutate vendored terrain geometry.

These are PyDCS authoring rectangles, not surveyed DCS terrain/detail limits.
Cache only immutable bounds and a projection, never airports/parking state.
"""
from functools import lru_cache
import math


def normalized_bounds(terrain):
    b = terrain.bounds
    return (min(b.bottom, b.top), max(b.bottom, b.top),
            min(b.left, b.right), max(b.left, b.right))


def contains(bounds, x, y):
    return (math.isfinite(x) and math.isfinite(y)
            and bounds[0]-1e-5 <= x <= bounds[1]+1e-5
            and bounds[2]-1e-5 <= y <= bounds[3]+1e-5)


@lru_cache(maxsize=32)
def _frame(map_key):
    from pyproj import CRS, Transformer
    from .resolver import load_json, resolve_terrain
    cfg = load_json('maps')[map_key]
    terrain = resolve_terrain(cfg['terrain_class'])()
    x_min, x_max, y_min, y_max = normalized_bounds(terrain)
    points = [(a.position.x, a.position.y) for a in terrain.airports.values()]
    if 'carrier' in cfg:
        anchor = cfg['carrier']['anchor']
        points.append((anchor['x'], anchor['y']))
    bounds = (min([x_min]+[x for x,y in points]), max([x_max]+[x for x,y in points]),
              min([y_min]+[y for x,y in points]), max([y_max]+[y for x,y in points]))
    return (bounds,
            Transformer.from_crs(CRS('WGS84'), terrain.projection_parameters.to_crs()))


def check_position(value, map_key, name):
    from .recipe import RecipeError
    bounds, projection = _frame(map_key)
    x, y = (projection.transform(value['lat'], value['lon']) if 'lat' in value
            else (value['x'], value['y']))
    if not contains(bounds, x, y):
        raise RecipeError(f'{name} is outside the selected map bounds for {map_key}; '
                          'inspect bounds in the maps catalog (DCS x/y metres).')


def catalog_bounds(map_key):
    bounds, _ = _frame(map_key)
    return dict(zip(('x_min', 'x_max', 'y_min', 'y_max'), bounds),
                coordinate_system='DCS theatre local', units='metres',
                axes={'x': 'north', 'y': 'east'}, inclusive=True,
                source='normalized vendored PyDCS rectangle expanded to include known airfields and configured carrier anchors',
                coverage='Authoring envelope only; not certified DCS terrain/detail or safe-flight coverage. '
                         'WGS84 lat/lon inputs are projected before this check.')
