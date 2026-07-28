__version__ = "1.34.1"

# Preflight: vendored pydcs imports pyproj at import time (terrain projections).
# Fail with instructions instead of a bare ModuleNotFoundError deep in pydcs.
try:
    import pyproj  # noqa: F401
except ImportError as _e:
    raise ImportError(
        "DCS Sortie Starter requires 'pyproj' (used by pydcs terrain "
        "projections). Install it with:  pip install -r requirements.txt  "
        "(or: pip install pyproj)") from _e

from . import _determinism  # noqa: F401  (patches pydcs for cross-process reproducibility)
from .terrains import install as _install_terrains
_install_terrains()  # register extension maps (Afghanistan...) in pydcs's loader
from .dtc import install_unit_dtc as _install_unit_dtc
_install_unit_dtc()  # patch pydcs to serialise the unit-level F-14B(U) DTC link
from .recipe import Recipe
from .builder import StarterBuilder, generate
