"""Entry point: `python run.py` -> serve the app on localhost."""
from __future__ import annotations

import webbrowser

import uvicorn

from app.config import SETTINGS

if __name__ == "__main__":
    url = f"http://{SETTINGS.host}:{SETTINGS.port}"
    print(f"\n  Storage Screener running at {url}\n  (Ctrl+C to stop)\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    uvicorn.run("app.main:app", host=SETTINGS.host, port=SETTINGS.port, reload=False)
