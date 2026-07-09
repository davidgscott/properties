@echo off
REM Storage Screener - one-click updater for Windows.
REM Downloads the latest version and swaps in the new files. Your saved listings
REM and installed setup are kept. After it finishes, run start.bat as usual.

cd /d "%~dp0"

echo ============================================
echo    Updating Storage Screener
echo ============================================
echo.
echo Downloading the latest version...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri 'https://github.com/davidgscott/properties/archive/refs/heads/main.zip' -OutFile 'update.zip'; if (Test-Path 'update_tmp') { Remove-Item -Recurse -Force 'update_tmp' }; Expand-Archive -Path 'update.zip' -DestinationPath 'update_tmp' -Force"
if errorlevel 1 (
  echo.
  echo Update failed to download. Check your internet connection and try again.
  pause
  exit /b 1
)

echo Installing new files...
REM /E = include subfolders; no /MIR so your .venv and saved listings are kept.
REM /XF skips this running script to avoid overwriting it mid-run.
robocopy update_tmp\properties-main . /E /XF update.bat update.command /NFL /NDL /NJH /NJS /NP >nul
REM robocopy exit codes 0-7 mean success; 8 or higher is a real error.
if %ERRORLEVEL% GEQ 8 (
  echo.
  echo Update failed while copying files.
  powershell -NoProfile -Command "Remove-Item -Recurse -Force 'update_tmp','update.zip' -ErrorAction SilentlyContinue"
  pause
  exit /b 1
)

powershell -NoProfile -Command "Remove-Item -Recurse -Force 'update_tmp','update.zip' -ErrorAction SilentlyContinue"

echo.
echo Update complete!
echo Now double-click start.bat to run it, and press Ctrl+F5 in your browser.
pause
