@echo off
cd /d %~dp0
where py >nul 2>nul
if %errorlevel%==0 (
  set PY_CMD=py -3
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set PY_CMD=python
  ) else (
    echo Python was not found.
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    pause
    exit /b 1
  )
)

if not exist .venv (
  %PY_CMD% -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Install complete.
echo Examples:
if exist run_baseline.bat echo   run_baseline.bat
if exist run_max_single_weight_3way.bat echo   run_max_single_weight_3way.bat
if exist run_preset.bat echo   run_preset.bat presets\edge_param_scan.json
pause
