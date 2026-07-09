"""Slope source: approximate parcel slope from USGS 3DEP elevation.

Primary: 3DEP ImageServer `getSamples` returns an NxN elevation grid over the
parcel bbox in ONE request (auto-uses 1 m LiDAR where flown). We fit slope from
finite differences and report mean + max slope in percent.
Fallback: EPQS per-point queries if getSamples is unavailable.

Slope % = rise/run * 100. A near-flat pad for self-storage is typically < ~8%.
"""
from __future__ import annotations

import json
import math

import httpx
import numpy as np

from ..config import ELEVATION_3DEP_URL, EPQS_URL


def _grid_points(bbox: list[float], n: int) -> list[list[float]]:
    w, s, e, nth = bbox
    xs = np.linspace(w, e, n)
    ys = np.linspace(s, nth, n)
    return [[float(x), float(y)] for y in ys for x in xs]


def _meters_per_deg(lat: float) -> tuple[float, float]:
    """Approx meters per degree lon/lat at a given latitude."""
    m_lat = 111_132.0
    m_lon = 111_320.0 * math.cos(math.radians(lat))
    return m_lon, m_lat


async def slope_for_parcel(
    client: httpx.AsyncClient, bbox: list[float], grid: int = 3,
) -> dict:
    """Return {mean_pct, max_pct, method} slope estimate for the parcel bbox."""
    pts = _grid_points(bbox, grid)
    elevations = await _get_samples(client, pts)
    if elevations is None or any(v is None for v in elevations):
        elevations = await _epqs_grid(client, pts)
    if elevations is None or any(v is None for v in elevations):
        return {"mean_pct": None, "max_pct": None, "method": "unavailable"}

    z = np.array(elevations, dtype=float).reshape(grid, grid)
    lat = (bbox[1] + bbox[3]) / 2.0
    m_lon, m_lat = _meters_per_deg(lat)
    dx = (bbox[2] - bbox[0]) / (grid - 1) * m_lon
    dy = (bbox[3] - bbox[1]) / (grid - 1) * m_lat
    if dx <= 0 or dy <= 0:
        return {"mean_pct": None, "max_pct": None, "method": "degenerate"}

    gy, gx = np.gradient(z, dy, dx)
    slope = np.sqrt(gx**2 + gy**2)  # rise/run
    return {
        "mean_pct": round(float(np.mean(slope)) * 100, 1),
        "max_pct": round(float(np.max(slope)) * 100, 1),
        "method": "3dep",
    }


async def _get_samples(client: httpx.AsyncClient, pts: list[list[float]]):
    params = {
        "geometry": json.dumps({"points": pts, "spatialReference": {"wkid": 4326}}),
        "geometryType": "esriGeometryMultipoint",
        "returnFirstValueOnly": "true",
        "f": "json",
    }
    try:
        r = await client.post(f"{ELEVATION_3DEP_URL}/getSamples", data=params, timeout=45)
        r.raise_for_status()
        data = r.json()
        samples = data.get("samples", [])
        # Samples come back in request order.
        vals = []
        for s in samples:
            v = s.get("value")
            vals.append(float(v) if v not in (None, "", "NoData") else None)
        return vals if len(vals) == len(pts) else None
    except Exception:
        return None


async def _epqs_grid(client: httpx.AsyncClient, pts: list[list[float]]):
    vals = []
    for x, y in pts:
        try:
            r = await client.get(
                EPQS_URL,
                params={"x": x, "y": y, "units": "Meters", "wkid": 4326, "includeDate": "false"},
                timeout=30,
            )
            r.raise_for_status()
            d = r.json()
            v = d.get("value")
            vals.append(float(v) if v not in (None, "") else None)
        except Exception:
            vals.append(None)
    return vals
