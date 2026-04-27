@echo off
cd /d %~dp0
if not exist .venv\Scripts\activate.bat (
  echo Virtual environment not found. Please run install.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
set MPLBACKEND=Agg
if "%~1"=="" (
  echo Usage: run_preset.bat presets\xxx.json
  pause
  exit /b 1
)
python core\run_preset.py %1
pause
