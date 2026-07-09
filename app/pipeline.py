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
    build_where, parcels_where, parcels_by_apn, radius_bbox, haversine_miles,
    is_vacant, vacant_category, situs_address,
)
from .sources.slope import slope_for_parcel
from .sources.zoning import zoning_for_parcel


async def screen_area(*, thresholds: Thresholds, bbox: list[float] | None = None,
                      center: tuple[float, float] | None = None,
                      radius_miles: float | None = None,
                      only_vacant: bool = True,
                      commercial_only: bool = False,
                      unincorporated_only: bool = True) -> dict:
    """Screen an area given either a bbox or a center + mile radius.

    The vacant/size filter is pushed into the parcel query (server-side) so a
    large radius stays tractable; candidates are then clipped to the circle,
    prioritised by acreage, and capped before the expensive enrichment.
    """
    limits = SETTINGS.screen
    listed_map = listings_store.by_apn()

    query_bbox = bbox
    if center is not None and radius_miles:
        query_bbox = radius_bbox(center, radius_miles)
    if query_bbox is None:
        raise ValueError("Provide a bbox or center+radius_miles.")

    where = build_where(only_vacant=only_vacant, min_acres=thresholds.min_acres,
                        commercial_only=commercial_only,
                        unincorporated_only=unincorporated_only)

    async with httpx.AsyncClient(headers={"User-Agent": "StorageScreener/0.1"}) as client:
        raw = await parcels_where(client, query_bbox, where)
        # Always include manually-listed parcels even if they don't match the
        # vacant/size filter (a listing means the buyer cares about it).
        have = {_apn_norm(f["attributes"].get("APN")) for f in raw}
        extra_apns = [lm["apn"] for k, lm in listed_map.items()
                      if k and k not in have and lm.get("apn")]
        if extra_apns:
            raw += await parcels_by_apn(client, extra_apns)

        candidates = []
        for feat in raw:
            a = feat.get("attributes", {})
            geom = feat.get("geometry")
            if not geom:
                continue
            shape = arcgis_to_shapely(geom)
            if shape is None or shape.is_empty:
                continue
            lon, lat = centroid_lonlat(shape)
            # Clip to the circle when in radius mode.
            if center is not None and radius_miles:
                if haversine_miles(center[0], center[1], lon, lat) > radius_miles:
                    continue
            apn_norm = _apn_norm(a.get("APN"))
            candidates.append({
                "feat": feat, "shape": shape, "lon": lon, "lat": lat,
                "vacant": is_vacant(a), "listed": apn_norm in listed_map,
                "listing": listed_map.get(apn_norm),
                "acres": a.get("LandSizeAcres") or 0,
            })

        in_area = len(candidates)
        # Prioritise larger parcels (more likely to fit a facility) and always
        # keep listed ones near the front.
        candidates.sort(key=lambda c: (c["listed"], c["acres"]), reverse=True)
        truncated = in_area > limits.max_parcels
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
        "in_area": in_area,
        "truncated": truncated,
        "max_parcels": limits.max_parcels,
        "where": where,
        "results": results,
    }


def _apn_norm(apn: str | None) -> str:
    return "".join(ch for ch in (apn or "") if ch.isalnum())


async def _enrich_one(client, item, thresholds: Thresholds, slope_grid: int):
    feat = item["feat"]
    vacant, listed, listing = item["vacant"], item["listed"], item["listing"]
    a = feat["attributes"]
    geom = feat["geometry"]
    shape = item["shape"]
    lon, lat = item["lon"], item["lat"]
    pbbox = bbox_of(shape)

    juris, zoning, flood, slope = await asyncio.gather(
        jurisdiction_for_point(client, lon, lat),
        zoning_for_parcel(client, geom, shape),
        flood_for_parcel(client, geom, shape),
        slope_for_parcel(client, pbbox, grid=slope_grid),
    )

    verdict = zoning_lookup(juris, zoning["districts"])
    zoning_note = verdict["note"]
    if len(zoning["districts"]) > 1:
        zoning_note = (f"Parcel spans {', '.join(zoning['districts'])}; verdict "
                       f"reflects {verdict.get('zone')}. " + zoning_note)
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
        # Show the zone the verdict is based on (the most storage-favorable zone
        # the parcel touches); fall back to the dominant-by-area zone.
        "zoning": verdict.get("zone") or zoning["dominant"],
        "zoning_dominant": zoning["dominant"],
        "zoning_all": zoning["districts"],
        "zoning_base": zoning.get("dominant_base"),
        "storage_permitted": verdict["permitted"],
        "permit_type": verdict["permit_type"],
        "zoning_confidence": verdict["confidence"],
        "zoning_note": zoning_note,
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
