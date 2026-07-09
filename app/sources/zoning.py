"""Zoning source: resolve a parcel's zoning district(s).

For unincorporated county we query the authoritative Permit Sonoma base-zoning
layer with the parcel polygon (intersects) and return every district the parcel
touches, plus the dominant one by overlap area. City parcels fall outside this
layer and come back with no district -> flagged for manual city lookup.
"""
from __future__ import annotations

import httpx

from ..arcgis import query_features
from ..config import ZONING_URL, ZONING_CODE_FIELD
from ..geometry import arcgis_to_shapely, overlap_fraction


async def zoning_for_parcel(
    client: httpx.AsyncClient, parcel_geom_arcgis: dict, parcel_shape,
) -> dict:
    """Return {districts: [...], dominant: code|None, coverage: 0..1}."""
    data = await query_features(
        client, ZONING_URL,
        geometry=parcel_geom_arcgis, geometry_type="esriGeometryPolygon",
        out_fields=f"{ZONING_CODE_FIELD},BASEZONING,DENSITY",
        return_geometry=True,
    )
    feats = data.get("features", [])
    scored: list[tuple[str, float, str]] = []
    for f in feats:
        code = f["attributes"].get(ZONING_CODE_FIELD)
        base = f["attributes"].get("BASEZONING") or code
        zshape = arcgis_to_shapely(f.get("geometry"))
        frac = overlap_fraction(parcel_shape, zshape) if zshape else 0.0
        if code:
            scored.append((code, frac, base))
    scored.sort(key=lambda x: x[1], reverse=True)
    # Districts ordered by overlap (dominant first) so downstream reasons cite
    # the dominant zone, de-duplicated while preserving that order.
    districts: list[str] = []
    for c, _, _ in scored:
        if c not in districts:
            districts.append(c)
    dominant = scored[0][0] if scored else None
    coverage = scored[0][1] if scored else 0.0
    return {
        "districts": districts,
        "dominant": dominant,
        "dominant_base": scored[0][2] if scored else None,
        "coverage": round(coverage, 3),
    }
