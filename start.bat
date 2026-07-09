@echo off
REM Storage Screener - double-click launcher for Windows.
REM First run installs everything (a few minutes); later runs start in seconds.
REM To stop the tool: close this window, or press Ctrl+C.

cd /d "%~dp0"

echo ======================================
echo    Storage Screener
echo ======================================
echo.

REM 1) Find a Python interpreter. Prefer the official "py" launcher (from
REM    python.org), then fall back to "python". Using "py" avoids the
REM    Microsoft Store placeholder that can hijack the "python" command.
set "PYEXE="
py -3 --version >nul 2>nul && set "PYEXE=py -3"
if not defined PYEXE (
  python --version >nul 2>nul && set "PYEXE=python"
)
if not defined PYEXE (
  echo Python is not installed yet.
  echo Opening the download page - install Python, then double-click this file again.
  echo IMPORTANT: on the first installer screen, check "Add Python to PATH".
  start "" "https://www.python.org/downloads/"
  echo.
  pause
  exit /b 1
)

REM 2) First-time setup: create an isolated environment and install components.
if not exist ".venv" (
  echo First-time setup - installing components. This can take a few minutes...
  %PYEXE% -m venv .venv
  if errorlevel 1 (
    echo Could not create the environment.
    pause
    exit /b 1
  )
  call ".venv\Scripts\activate.bat"
  python -m pip install --upgrade pip >nul
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Install failed. Check your internet connection and try again.
    pause
    exit /b 1
  )
  echo Setup complete.
  echo.
) else (
  call ".venv\Scripts\activate.bat"
)

REM 3) Launch. run.py opens your browser to http://127.0.0.1:8000
echo Starting Storage Screener - your browser will open in a moment.
echo Leave this window open while you use the tool. Press Ctrl+C to stop.
echo.
python run.py

echo.
echo The tool has stopped.
pause
