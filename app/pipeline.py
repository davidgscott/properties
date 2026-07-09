"""Screening pipeline: raw parcels -> enriched, scored candidates.

Flow (per the approved plan):
  1. Query parcels in the area of interest (bbox).
  2. Cheap prefilter: minimum acreage + (vacant OR manually listed).
  3. Enrich each survivor concurrently: jurisdiction, zoning district,
     storage-permit verdict, FEMA SFHA overlap, slope.
  4. Score -> PASS / REVIEW / FAIL with reasons, and build outbound links.

Only prefiltered parcels get the expensive flood/slope/zoning calls, and the
count is capped (max_parcels) to stay polite to the public services.
"""
from __future__ import annotations

import asyncio

import httpx

from . import listings as listings_store
from .config import LINKS, SETTINGS, Thresholds
from .geometry import arcgis_to_shapely, centroid_lonlat, bbox_of, geojson_coords
from .rules.scoring import score_parcel
from .rules.storage_zoning import lookup as zoning_lookup
from .sources.flood import flood_for_parcel
from .sources.jurisdiction import jurisdiction_for_point
from .sources.parcels import (
    parcels_in_bbox, is_vacant, vacant_category, situs_address,
)
from .sources.slope import slope_for_parcel
from .sources.zoning import zoning_for_parcel


async def screen_bbox(bbox: list[float], *, thresholds: Thresholds,
                      only_vacant: bool = True) -> dict:
    limits = SETTINGS.screen
    listed_map = listings_store.by_apn()

    async with httpx.AsyncClient(headers={"User-Agent": "StorageScreener/0.1"}) as client:
        raw = await parcels_in_bbox(client, bbox)

        # Prefilter (cheap, local).
        candidates = []
        for feat in raw:
            a = feat.get("attributes", {})
            geom = feat.get("geometry")
            if not geom:
                continue
            acres = a.get("LandSizeAcres")
            apn_norm = "".join(ch for ch in (a.get("APN") or "") if ch.isalnum())
            listed = apn_norm in listed_map
            vacant = is_vacant(a)
            if acres is not None and acres < thresholds.min_acres and not listed:
                continue
            if only_vacant and not vacant and not listed:
                continue
            candidates.append((feat, vacant, listed, listed_map.get(apn_norm)))

        truncated = len(candidates) > limits.max_parcels
        candidates = candidates[: limits.max_parcels]

        sem = asyncio.Semaphore(limits.concurrency)

        async def enrich(item):
            async with sem:
                return await _enrich_one(client, item, thresholds, limits.slope_grid)

        results = await asyncio.gather(*(enrich(c) for c in candidates))

    results = [r for r in results if r]
    order = {"PASS": 0, "REVIEW": 1, "FAIL": 2}
    results.sort(key=lambda r: (order.get(r["status"], 3), -r["score"]))
    return {
        "count": len(results),
        "scanned": len(raw),
        "truncated": truncated,
        "max_parcels": limits.max_parcels,
        "results": results,
    }


async def _enrich_one(client, item, thresholds: Thresholds, slope_grid: int):
    feat, vacant, listed, listing = item
    a = feat["attributes"]
    geom = feat["geometry"]
    shape = arcgis_to_shapely(geom)
    if shape is None or shape.is_empty:
        return None

    lon, lat = centroid_lonlat(shape)
    pbbox = bbox_of(shape)

    juris, zoning, flood, slope = await asyncio.gather(
        jurisdiction_for_point(client, lon, lat),
        zoning_for_parcel(client, geom, shape),
        flood_for_parcel(client, geom, shape),
        slope_for_parcel(client, pbbox, grid=slope_grid),
    )

    verdict = zoning_lookup(juris, zoning["districts"])
    acres = a.get("LandSizeAcres")
    scored = score_parcel(
        flood=flood, zoning_verdict=verdict, slope=slope,
        acres=acres, vacant=vacant, listed=listed, th=thresholds,
    )

    apn = a.get("APN") or ""
    return {
        "apn": apn,
        "address": situs_address(a),
        "jurisdiction": juris,
        "zoning": zoning["dominant"],
        "zoning_all": zoning["districts"],
        "zoning_base": zoning.get("dominant_base"),
        "storage_permitted": verdict["permitted"],
        "permit_type": verdict["permit_type"],
        "zoning_confidence": verdict["confidence"],
        "zoning_note": verdict["note"],
        "zoning_verify_url": verdict.get("verify_url"),
        "flood_zone": ",".join(flood["zones"]) or "X / none",
        "sfha_pct": flood["sfha_pct"],
        "in_sfha": flood["in_sfha"],
        "floodway": flood["floodway"],
        "slope_mean_pct": slope["mean_pct"],
        "slope_max_pct": slope["max_pct"],
        "acres": round(acres, 2) if acres is not None else None,
        "use_code_desc": a.get("UseCodeDescription"),
        "vacant": vacant,
        "vacant_category": vacant_category(a),
        "listed": listed,
        "list_price": (listing or {}).get("price"),
        "listing_url": (listing or {}).get("url"),
        "status": scored["status"],
        "score": scored["score"],
        "reasons": scored["reasons"],
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "geometry": geojson_coords(shape),
        "links": _links(apn, lat, lon),
    }


def _links(apn: str, lat: float, lon: float) -> dict:
    return {
        "county": LINKS["county_parcel_report"].format(apn=apn),
        "google_maps": LINKS["google_maps"].format(lat=lat, lon=lon),
        "regrid": LINKS["regrid"].format(apn=apn),
        "fema": LINKS["fema_msc"].format(lat=lat, lon=lon),
    }
