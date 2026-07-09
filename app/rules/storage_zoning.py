"""Storage-permitted rule engine — loads the editable zoning lookup table.

Given a jurisdiction and one or more zone codes touching a parcel, returns
whether self-storage is permitted, the permit path, confidence, and a
verification link. Unknown / unmapped codes return an explicit 'unknown' so the
scorer can flag them for manual review rather than silently pass or fail.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_LOOKUP_PATH = Path(__file__).with_name("zoning_lookup.yaml")


@lru_cache(maxsize=1)
def _table() -> dict:
    return yaml.safe_load(_LOOKUP_PATH.read_text())


def _article_url(article: str | None) -> str | None:
    if not article:
        return None
    base = _table().get("meta", {}).get("county_code_base", "")
    # e.g. article "26-34" -> .../coor_ch26_art34
    try:
        art_no = article.split("-")[1]
        return f"{base}_art{art_no}"
    except Exception:
        return base or None


def _match_jurisdiction(jurisdiction: str) -> str | None:
    juris = _table().get("jurisdictions", {})
    if jurisdiction in juris:
        return jurisdiction
    low = jurisdiction.lower()
    for key in juris:
        k = key.lower()
        if k in low or low in k:
            return key
    return None


def lookup(jurisdiction: str, zone_codes: list[str]) -> dict:
    """Return the storage-permit verdict for a parcel's zone code(s)."""
    juris_key = _match_jurisdiction(jurisdiction)
    if juris_key is None:
        return _verdict(None, "unknown", "low", None, None,
                        f"No lookup for jurisdiction '{jurisdiction}'. Verify manually.")
    zones = _table()["jurisdictions"][juris_key].get("zones") or {}
    if not zone_codes:
        return _verdict(None, "unknown", "low", juris_key, None,
                        "No zoning district resolved for this parcel.")

    best = None
    for code in zone_codes:
        entry = zones.get(code)
        if entry is None:
            cand = _verdict(None, "unknown", "low", juris_key, code,
                            f"Zone '{code}' not mapped for {juris_key}. Verify.")
        else:
            cand = _verdict(
                entry.get("permitted"), entry.get("permit_type", "unknown"),
                entry.get("confidence", "low"), juris_key, code,
                entry.get("note", ""), _article_url(entry.get("article")),
            )
        best = _prefer(best, cand)
    return best


# Rank verdicts so the most favourable permitted status wins when a parcel
# straddles multiple zones (a permitted zone beats a not-allowed one).
_RANK = {("by-right", True): 5, ("conditional", True): 4,
         ("unknown", None): 3, ("not-allowed", False): 1}


def _prefer(a: dict | None, b: dict) -> dict:
    if a is None:
        return b
    ra = _RANK.get((a["permit_type"], a["permitted"]), 2)
    rb = _RANK.get((b["permit_type"], b["permitted"]), 2)
    return b if rb > ra else a


def _verdict(permitted, permit_type, confidence, juris, zone, note, url=None) -> dict:
    return {
        "permitted": permitted,
        "permit_type": permit_type,
        "confidence": confidence,
        "jurisdiction": juris,
        "zone": zone,
        "note": note,
        "verify_url": url,
    }
