"""Geometry helpers: ArcGIS <-> shapely, overlap %, centroid, bbox.

Screening percentages are computed as area RATIOS in WGS84 planar space. Over a
single small parcel the local scale distortion is nearly constant, so the ratio
(intersection area / parcel area) is accurate enough for a screening flag. This
is not survey-grade area math.
"""
from __future__ import annotations

from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union
from shapely.validation import make_valid


def arcgis_to_shapely(geom: dict):
    """Convert an ArcGIS polygon ({"rings": [...]}) to a shapely geometry."""
    if not geom or "rings" not in geom:
        return None
    rings = geom["rings"]
    if not rings:
        return None
    # Ring 0 is the exterior; remaining rings are treated as holes if they sit
    # inside it, else as separate polygons. Parcels rarely have holes, so this
    # simple heuristic is sufficient.
    exterior = Polygon(rings[0])
    holes = []
    extras = []
    for r in rings[1:]:
        poly = Polygon(r)
        if exterior.contains(poly.representative_point()):
            holes.append(r)
        else:
            extras.append(poly)
    result = Polygon(rings[0], holes) if holes else exterior
    if extras:
        result = unary_union([result, *extras])
    if not result.is_valid:
        result = make_valid(result)
    return result


def geojson_coords(geom) -> list:
    """Return GeoJSON-style coordinates for a shapely (multi)polygon."""
    gj = geom.__geo_interface__
    return gj


def overlap_fraction(parcel, other) -> float:
    """Fraction of `parcel` area covered by `other` (0..1)."""
    if parcel is None or other is None or parcel.area == 0:
        return 0.0
    try:
        inter = parcel.intersection(other)
        return max(0.0, min(1.0, inter.area / parcel.area))
    except Exception:
        return 0.0


def centroid_lonlat(geom) -> tuple[float, float]:
    c = geom.representative_point()
    return (c.x, c.y)


def bbox_of(geom) -> list[float]:
    minx, miny, maxx, maxy = geom.bounds
    return [minx, miny, maxx, maxy]
