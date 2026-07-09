"""Thin async ArcGIS REST helper with a polite on-disk cache.

All outbound calls to FEMA / county / USGS services funnel through here so we
cache responses, throttle politely, and keep one place to reason about SR and
paging.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import httpx

from .config import CACHE_DIR

CACHE_DIR.mkdir(parents=True, exist_ok=True)
_CACHE_TTL = 60 * 60 * 24 * 7  # 7 days; parcels/zoning/flood change slowly


def _cache_path(key: str) -> Any:
    h = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def _cache_get(key: str) -> Any | None:
    p = _cache_path(key)
    if not p.exists():
        return None
    try:
        blob = json.loads(p.read_text())
        if time.time() - blob["t"] > _CACHE_TTL:
            return None
        return blob["v"]
    except Exception:
        return None


def _cache_put(key: str, value: Any) -> None:
    try:
        _cache_path(key).write_text(json.dumps({"t": time.time(), "v": value}))
    except Exception:
        pass


async def _request(
    client: httpx.AsyncClient, url: str, params: dict, method: str = "POST"
) -> dict:
    """Fetch a JSON response, using cache. POST by default (large geometries)."""
    key = f"{method}:{url}:{json.dumps(params, sort_keys=True, default=str)}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            if method == "GET":
                r = await client.get(url, params=params, timeout=45)
            else:
                r = await client.post(url, data=params, timeout=45)
            r.raise_for_status()
            data = r.json()
            # ArcGIS returns HTTP 200 with an {"error": ...} body on failure.
            if isinstance(data, dict) and "error" in data:
                raise RuntimeError(data["error"])
            _cache_put(key, data)
            return data
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            await _sleep(0.6 * (attempt + 1))
    raise RuntimeError(f"ArcGIS request failed for {url}: {last_exc}")


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


async def query_features(
    client: httpx.AsyncClient,
    layer_url: str,
    *,
    where: str = "1=1",
    geometry: dict | None = None,
    geometry_type: str = "esriGeometryEnvelope",
    spatial_rel: str = "esriSpatialRelIntersects",
    out_fields: str = "*",
    return_geometry: bool = True,
    out_sr: int = 4326,
    in_sr: int = 4326,
    result_offset: int = 0,
    result_record_count: int | None = None,
) -> dict:
    """Run a `/query` against an ArcGIS feature/map layer."""
    params: dict[str, Any] = {
        "where": where,
        "outFields": out_fields,
        "returnGeometry": "true" if return_geometry else "false",
        "outSR": out_sr,
        "spatialRel": spatial_rel,
        "resultOffset": result_offset,
        "f": "json",
    }
    if geometry is not None:
        params["geometry"] = json.dumps(geometry)
        params["geometryType"] = geometry_type
        params["inSR"] = in_sr
    if result_record_count is not None:
        params["resultRecordCount"] = result_record_count
    return await _request(client, f"{layer_url}/query", params, method="POST")


def envelope(bbox: list[float]) -> dict:
    """[w,s,e,n] -> ArcGIS envelope geometry (WGS84)."""
    w, s, e, n = bbox
    return {"xmin": w, "ymin": s, "xmax": e, "ymax": n,
            "spatialReference": {"wkid": 4326}}
