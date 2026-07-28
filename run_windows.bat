@echo off
REM DCS Sortie Starter - Windows launcher.
REM Double-click this file in Explorer. First run sets everything up (needs
REM internet); later runs start instantly.
setlocal
cd /d "%~dp0"

echo === DCS Sortie Starter ===

REM 1. Python check
where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required. Install it from https://www.python.org/downloads/
  echo IMPORTANT: tick "Add python.exe to PATH" in the installer, then rerun this file.
  pause
  exit /b 1
)

REM 2. Virtual environment
if not exist .venv (
  echo First run: creating environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

REM 3. Dependencies
python -c "import fastapi, uvicorn, PIL, pyproj" >nul 2>&1
if errorlevel 1 (
  echo Installing dependencies ^(one-time, ~1 minute^)...
  python -m pip install --quiet --upgrade pip
  python -m pip install --quiet fastapi "uvicorn[standard]" pillow pyproj
)

REM 4. pydcs ships vendored in this package (vendor\dcs) - no extra install.
set PYTHONPATH=%CD%\vendor;%PYTHONPATH%
python -c "from dcs import planes; assert hasattr(planes,'F_4E_45MC'); print('pydcs OK (vendored)')"
if errorlevel 1 (
  echo Vendored pydcs failed to load. Stopping.
  pause
  exit /b 1
)

REM 5. Launch and open the browser
echo.
echo Starting DCS Sortie Starter at http://127.0.0.1:8000
echo Leave this window open while you use it. Ctrl+C to stop.
start "" /b cmd /c "timeout /t 3 >nul && start http://127.0.0.1:8000"
python -m uvicorn server.app:app --host 127.0.0.1 --port 8000

pause
