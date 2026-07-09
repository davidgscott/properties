"""Jurisdiction resolver: which city (if any) contains a parcel centroid.

Parcels outside every incorporated city limit are 'Unincorporated' -> Sonoma
County / Permit Sonoma is the zoning authority (this is Guerneville's case).
"""
from __future__ import annotations

import httpx

from ..arcgis import query_features
from ..config import CITY_LIMITS_URL

# Field on the city-limits layer holding the city name (resolved at runtime).
_NAME_FIELDS = ("CITY", "NAME", "CITYNAME", "City", "Name", "JURISDICTION")


async def jurisdiction_for_point(client: httpx.AsyncClient, lon: float, lat: float) -> str:
    try:
        data = await query_features(
            client, CITY_LIMITS_URL,
            geometry={"x": lon, "y": lat, "spatialReference": {"wkid": 4326}},
            geometry_type="esriGeometryPoint",
            out_fields="*", return_geometry=False,
        )
        feats = data.get("features", [])
        if not feats:
            return "Unincorporated (Sonoma County)"
        attrs = feats[0]["attributes"]
        for fld in _NAME_FIELDS:
            if attrs.get(fld):
                return str(attrs[fld])
        # Fall back to the first string attribute that looks like a place name.
        for v in attrs.values():
            if isinstance(v, str) and v.strip():
                return v
        return "Incorporated city"
    except Exception:
        return "Unknown"
