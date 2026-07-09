#!/bin/bash
# Storage Screener — double-click launcher for macOS.
# First run installs everything (a few minutes); later runs start in seconds.
# To stop the tool: close this window, or press Control-C.

cd "$(dirname "$0")" || exit 1

echo "======================================"
echo "   Storage Screener"
echo "======================================"
echo

# 1) Make sure Python 3 is available.
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is not installed yet."
  echo "Opening the download page — install Python, then double-click this file again."
  open "https://www.python.org/downloads/" 2>/dev/null
  echo
  read -r -p "Press Return to close."
  exit 1
fi

# 2) First-time setup: create an isolated environment and install components.
if [ ! -d ".venv" ]; then
  echo "First-time setup — installing components. This can take a few minutes..."
  python3 -m venv .venv || { echo "Could not create the environment."; read -r -p "Press Return to close."; exit 1; }
  # shellcheck disable=SC1091
  source .venv/bin/activate
  python -m pip install --upgrade pip >/dev/null
  python -m pip install -r requirements.txt || { echo "Install failed. Check your internet connection and try again."; read -r -p "Press Return to close."; exit 1; }
  echo "Setup complete."
  echo
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

# 3) Launch. run.py opens your browser to http://127.0.0.1:8000
echo "Starting Storage Screener — your browser will open in a moment."
echo "Leave this window open while you use the tool. Press Control-C to stop."
echo
python run.py

# If the server stops, keep the window up so any message is readable.
read -r -p "The tool has stopped. Press Return to close."
