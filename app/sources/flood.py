"""FEMA flood source: parcel vs Special Flood Hazard Area (SFHA).

Queries FEMA NFHL Layer 28 (Flood Hazard Zones) with the parcel polygon, then
computes the exact fraction of the parcel inside any SFHA zone via shapely, and
flags floodway. Also checks the county's own F1 Floodway combining district as a
corroborating regulatory overlay.
"""
from __future__ import annotations

import httpx

from ..arcgis import query_features
from ..config import FEMA_NFHL_URL, COUNTY_FLOODWAY_F1_URL, SFHA_ZONES
from ..geometry import arcgis_to_shapely, overlap_fraction


async def flood_for_parcel(
    client: httpx.AsyncClient, parcel_geom_arcgis: dict, parcel_shape,
) -> dict:
    """Return flood screen: zones, % in SFHA, floodway flag, county overlay."""
    data = await query_features(
        client, FEMA_NFHL_URL,
        geometry=parcel_geom_arcgis, geometry_type="esriGeometryPolygon",
        out_fields="FLD_ZONE,SFHA_TF,ZONE_SUBTY,STATIC_BFE",
        return_geometry=True,
    )
    feats = data.get("features", [])
    zones: set[str] = set()
    sfha_area = 0.0
    floodway = False
    for f in feats:
        a = f["attributes"]
        zone = (a.get("FLD_ZONE") or "").strip()
        subty = (a.get("ZONE_SUBTY") or "").upper()
        if zone:
            zones.add(zone)
        is_sfha = zone in SFHA_ZONES or (a.get("SFHA_TF") == "T")
        if "FLOODWAY" in subty:
            floodway = True
        if is_sfha:
            fshape = arcgis_to_shapely(f.get("geometry"))
            if fshape:
                sfha_area += overlap_fraction(parcel_shape, fshape)
    sfha_pct = round(min(1.0, sfha_area) * 100, 1)

    county_floodway = await _county_floodway(client, parcel_geom_arcgis)

    return {
        "zones": sorted(zones),
        "sfha_pct": sfha_pct,
        "in_sfha": sfha_pct > 0,
        "floodway": floodway or county_floodway,
        "fema_floodway": floodway,
        "county_floodway": county_floodway,
    }


async def _county_floodway(client: httpx.AsyncClient, geom: dict) -> bool:
    try:
        data = await query_features(
            client, COUNTY_FLOODWAY_F1_URL,
            geometry=geom, geometry_type="esriGeometryPolygon",
            out_fields="OBJECTID", return_geometry=False,
        )
        return bool(data.get("features"))
    except Exception:
        return False
