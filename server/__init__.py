"""Server package bootstrap for vendored PyDCS in CLI and hosted installs."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if (ROOT / 'vendor/dcs').exists():
    sys.path.insert(0, str(ROOT / 'vendor'))
