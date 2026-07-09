"""Sonoma County parcel source + vacant-land classification.

Vacant detection uses three independent signals, any of which flags a parcel:
  1. UseCodeDescription contains "VACANT" (assessor land-use text)
  2. UseCodeType classifies it as vacant/undeveloped
  3. Value601Structure (assessed improvement value) is ~0
The exact vacant UseCodeDescription strings were confirmed at build time via the
layer's returnDistinctValues query.
"""
from __future__ import annotations

import httpx

from ..arcgis import query_features, envelope
from ..config import PARCELS_URL

# Fields we pull from the parcel layer.
PARCEL_FIELDS = ",".join([
    "APN", "SitusFormatted1", "SitusCity", "POCity", "CityType",
    "UseCode", "UseCodeDescription", "UseCodeType",
    "LandSizeAcres", "LandSizeSqft",
    "Value601Land", "Value601Structure", "URL",
])


def is_vacant(attrs: dict) -> bool:
    desc = (attrs.get("UseCodeDescription") or "").upper()
    utype = (attrs.get("UseCodeType") or "").upper()
    struct_val = attrs.get("Value601Structure")
    if "VACANT" in desc or "UNDEVEL" in desc:
        return True
    if utype == "VACANT":
        return True
    # No/near-zero improvement value is a strong vacant signal, but only trust it
    # when land itself is valued (filters out non-assessable/utility parcels).
    if struct_val is not None and struct_val <= 1000:
        land_val = attrs.get("Value601Land") or 0
        if land_val and land_val > 0:
            return True
    return False


def vacant_category(attrs: dict) -> str:
    """Human label for the vacancy classification (Commercial/Industrial/etc)."""
    desc = (attrs.get("UseCodeDescription") or "").upper()
    if "COMMERCIAL" in desc:
        return "Vacant commercial"
    if "INDUSTRIAL" in desc:
        return "Vacant industrial"
    if "RESIDENTIAL" in desc or "RES " in desc or "HOMESITE" in desc:
        return "Vacant residential"
    if "VACANT" in desc or "UNDEVEL" in desc:
        return "Vacant land"
    return "Improved / built"


async def parcels_in_bbox(
    client: httpx.AsyncClient, bbox: list[float], *, page_size: int = 1000,
    max_features: int = 4000,
) -> list[dict]:
    """Fetch all parcels intersecting a WGS84 bbox (paged)."""
    out: list[dict] = []
    offset = 0
    while len(out) < max_features:
        data = await query_features(
            client, PARCELS_URL,
            geometry=envelope(bbox), geometry_type="esriGeometryEnvelope",
            out_fields=PARCEL_FIELDS, return_geometry=True,
            result_offset=offset, result_record_count=page_size,
        )
        feats = data.get("features", [])
        if not feats:
            break
        out.extend(feats)
        if len(feats) < page_size and not data.get("exceededTransferLimit"):
            break
        offset += page_size
    return out


def situs_address(attrs: dict) -> str:
    addr = attrs.get("SitusFormatted1")
    if addr and addr.strip():
        return addr.strip()
    city = attrs.get("SitusCity") or attrs.get("POCity") or ""
    return f"(no situs address) {city}".strip()
