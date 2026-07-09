"""Sonoma County parcel source + vacant-land classification.

Vacant detection uses three independent signals, any of which flags a parcel:
  1. UseCodeDescription contains "VACANT" (assessor land-use text)
  2. UseCodeType classifies it as vacant/undeveloped
  3. Value601Structure (assessed improvement value) is ~0
The exact vacant UseCodeDescription strings were confirmed at build time via the
layer's returnDistinctValues query.
"""
from __future__ import annotations

import math

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


def build_where(*, only_vacant: bool, min_acres: float,
                commercial_only: bool, unincorporated_only: bool = True) -> str:
    """Build a server-side WHERE clause so large areas stay tractable.

    Pushing the vacant + acreage filter into the query means we pull hundreds of
    relevant parcels instead of tens of thousands. Listed parcels that don't
    match are re-added separately by the pipeline.
    """
    clauses: list[str] = []
    if unincorporated_only:
        # Restrict to unincorporated county — the only area the authoritative
        # county zoning layer covers (keeps out incorporated-city parcels whose
        # zoning we don't map).
        clauses.append("CityType = 'Unincorporated'")
    if only_vacant:
        vac = ("(UseCodeDescription LIKE '%VACANT%' OR "
               "UseCodeDescription LIKE '%UNDEVEL%')")
        if commercial_only:
            # Assessor classifies both vacant-commercial and vacant-industrial
            # land under UseCodeType 'Commercial'/'Industrial'.
            vac = ("(UseCodeDescription LIKE '%VACANT COMMERCIAL%' OR "
                   "UseCodeDescription LIKE '%VACANT INDUSTRIAL%' OR "
                   "(UseCodeDescription LIKE '%VACANT%' AND "
                   "UseCodeType IN ('Commercial','Industrial')))")
        clauses.append(vac)
    if min_acres and min_acres > 0:
        clauses.append(f"LandSizeAcres >= {float(min_acres)}")
    return " AND ".join(clauses) if clauses else "1=1"


async def parcels_where(
    client: httpx.AsyncClient, bbox: list[float], where: str, *,
    page_size: int = 1000, max_features: int = 6000,
) -> list[dict]:
    """Fetch parcels intersecting a WGS84 bbox that match `where` (paged)."""
    out: list[dict] = []
    offset = 0
    while len(out) < max_features:
        data = await query_features(
            client, PARCELS_URL, where=where,
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


async def parcels_by_apn(
    client: httpx.AsyncClient, apns: list[str],
) -> list[dict]:
    """Fetch specific parcels by APN (used to always include listed parcels)."""
    if not apns:
        return []
    quoted = ",".join("'" + a.replace("'", "") + "'" for a in apns)
    data = await query_features(
        client, PARCELS_URL, where=f"APN IN ({quoted})",
        out_fields=PARCEL_FIELDS, return_geometry=True,
    )
    return data.get("features", [])


def haversine_miles(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    r = 3958.7613  # earth radius, miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def radius_bbox(center: tuple[float, float], miles: float) -> list[float]:
    """Bounding box (WGS84) enclosing a mile-radius circle around center."""
    lon, lat = center
    dlat = miles / 69.0
    dlon = miles / (69.0 * max(0.1, math.cos(math.radians(lat))))
    return [lon - dlon, lat - dlat, lon + dlon, lat + dlat]


def situs_address(attrs: dict) -> str:
    addr = attrs.get("SitusFormatted1")
    if addr and addr.strip():
        return addr.strip()
    city = attrs.get("SitusCity") or attrs.get("POCity") or ""
    return f"(no situs address) {city}".strip()
