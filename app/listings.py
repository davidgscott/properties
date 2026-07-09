"""Manual listing store — the free 'for sale' path.

The buyer pastes LoopNet/Crexi/LandWatch listing URLs (+ optional APN and price);
the tool matches them to parcels by APN and enriches results. Persisted to a
small JSON file so entries survive restarts.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)
_STORE = DATA_DIR / "listings.json"


def _norm_apn(apn: str | None) -> str:
    return "".join(ch for ch in (apn or "") if ch.isalnum())


def load() -> list[dict]:
    if not _STORE.exists():
        return []
    try:
        return json.loads(_STORE.read_text())
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    _STORE.write_text(json.dumps(items, indent=2))


def add(entry: dict) -> list[dict]:
    items = load()
    entry["apn_norm"] = _norm_apn(entry.get("apn"))
    # Replace an existing listing for the same APN, else append.
    items = [i for i in items if i.get("apn_norm") != entry["apn_norm"] or not entry["apn_norm"]]
    items.append(entry)
    _save(items)
    return items


def delete(apn: str) -> list[dict]:
    items = [i for i in load() if i.get("apn_norm") != _norm_apn(apn)]
    _save(items)
    return items


def by_apn() -> dict[str, dict]:
    return {i["apn_norm"]: i for i in load() if i.get("apn_norm")}
