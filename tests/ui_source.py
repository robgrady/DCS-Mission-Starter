"""Read the shipped HTML and its explicitly referenced script modules for guards."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent.parent

def ui_source():
    path = ROOT / 'frontend/index.html'
    html = path.read_text()
    scripts = re.findall(r'<script src="/assets/([^"?]+)', html)
    return html + '\n' + '\n'.join((path.parent / 'assets' / name).read_text() for name in scripts)

def server_source():
    return '\n'.join(p.read_text() for p in sorted((ROOT / 'server').glob('*routes.py')))
