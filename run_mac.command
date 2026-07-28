#!/bin/bash
# DCS Sortie Starter — macOS launcher.
# Double-click this file in Finder (or run it in Terminal). First run sets
# everything up (needs internet); later runs start instantly.
set -e
cd "$(dirname "$0")"

echo "=== DCS Sortie Starter ==="

# 1. Python check (macOS will offer to install Command Line Tools if missing)
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/ and rerun."
  exit 1
fi

# 2. Virtual environment
if [ ! -d .venv ]; then
  echo "First run: creating environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

# 3. Dependencies — installed from requirements.txt, which is the single source
# of truth. A hand-maintained list here drifts: it silently missed
# python-multipart (needed by the admin login form) and the app refused to boot.
python -c "import fastapi, uvicorn, PIL, pyproj, multipart" 2>/dev/null || {
  echo "Installing dependencies (one-time, ~1 minute)..."
  pip install --quiet --upgrade pip
  pip install --quiet -r requirements.txt
}

# 4. pydcs ships vendored in this package (vendor/dcs) — no extra install.
export PYTHONPATH="$PWD/vendor:$PYTHONPATH"
python -c "from dcs import planes; assert hasattr(planes,'F_4E_45MC'); print('pydcs OK (vendored)')"

# 5. Launch and open the browser
echo ""
echo "Starting DCS Sortie Starter at http://127.0.0.1:8000"
echo "Leave this window open while you use it. Ctrl+C to stop."
( sleep 2 && open "http://127.0.0.1:8000" ) &
exec uvicorn server.app:app --host 127.0.0.1 --port 8000
