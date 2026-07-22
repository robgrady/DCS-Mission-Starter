__version__ = "1.21.0"

from . import _determinism  # noqa: F401  (patches pydcs for cross-process reproducibility)
from .terrains import install as _install_terrains
_install_terrains()  # register extension maps (Afghanistan...) in pydcs's loader
from .recipe import Recipe
from .builder import StarterBuilder, generate
