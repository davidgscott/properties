"""Central configuration: verified data endpoints, tunable thresholds, presets.

Every endpoint here was confirmed live against Sonoma County during build. If a
service is renamed or versioned, change it in this one module.
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "app"
WEB_DIR = ROOT / "web"
CACHE_DIR = APP_DIR / "cache"
DATA_DIR = APP_DIR / "data"

# --- Verified ArcGIS / REST endpoints ----------------------------------------

# Sonoma County parcels (seamless, includes parcels inside incorporated cities).
PARCELS_URL = (
    "https://socogis.sonomacounty.ca.gov/map/rest/services/"
    "AGCOMMPublic/Sonoma_County_Parcels/FeatureServer/0"
)

# Authoritative Permit Sonoma base zoning (DISTRICT holds the zone code, e.g.
# C3, M1, LC). Covers UNINCORPORATED county — stops at city limits.
ZONING_URL = (
    "https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services/"
    "Zoning_Area/FeatureServer/0"
)
ZONING_CODE_FIELD = "DISTRICT"

# FEMA National Flood Hazard Layer — Layer 28 = Flood Hazard Zones (S_FLD_HAZ_AR).
FEMA_NFHL_URL = (
    "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28"
)

# Sonoma County regulatory flood combining districts (bonus local overlays).
COUNTY_FLOODWAY_F1_URL = (
    "https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services/"
    "Floodway_F1/FeatureServer/0"
)
COUNTY_FLOODPLAIN_F2_URL = (
    "https://services1.arcgis.com/P5Mv5GY5S66M8Z1Q/arcgis/rest/services/"
    "Floodplain_F2/FeatureServer/0"
)

# City limits (jurisdiction resolver).
CITY_LIMITS_URL = (
    "https://socogis.sonomacounty.ca.gov/map/rest/services/"
    "PRMDPublic/City_Limits_Permit_Sonoma/FeatureServer/0"
)

# USGS 3DEP elevation (getSamples: many points, one request) + EPQS fallback.
ELEVATION_3DEP_URL = (
    "https://elevation.nationalmap.gov/arcgis/rest/services/"
    "3DEPElevation/ImageServer"
)
EPQS_URL = "https://epqs.nationalmap.gov/v1/json"

# FEMA zone codes that are Special Flood Hazard Areas (1% annual chance).
SFHA_ZONES = {"A", "AE", "AH", "AO", "AR", "A99", "V", "VE"}

# Outbound-link templates for each result row.
LINKS = {
    "county_parcel_report": "https://common3.mptsweb.com/megabyte/sonoma/asr/search?apn={apn}",
    "google_maps": "https://www.google.com/maps/search/?api=1&query={lat},{lon}",
    "regrid": "https://app.regrid.com/us/ca/sonoma#b=parcels&t={apn}",
    "fema_msc": "https://msc.fema.gov/portal/search?AddressQuery={lat}%2C{lon}",
}

# Community presets: name -> [west, south, east, north] bbox (WGS84).
COMMUNITIES: dict[str, list[float]] = {
    "Guerneville": [-123.030, 38.485, -122.965, 38.520],
    "Forestville": [-122.920, 38.460, -122.870, 38.490],
    "Monte Rio": [-123.020, 38.450, -122.980, 38.480],
    "Sebastopol": [-122.850, 38.380, -122.790, 38.420],
    "Windsor": [-122.840, 38.520, -122.780, 38.560],
    "Healdsburg": [-122.900, 38.600, -122.840, 38.640],
    "Cloverdale": [-123.040, 38.780, -123.000, 38.820],
    "Santa Rosa (NW)": [-122.780, 38.440, -122.700, 38.480],
}


@dataclass
class Thresholds:
    min_acres: float = 1.0
    max_slope_pct: float = 8.0
    sfha_fail_pct: float = 0.0


@dataclass
class ScreenLimits:
    max_parcels: int = 80
    slope_grid: int = 3
    concurrency: int = 6


@dataclass
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    thresholds: Thresholds = field(default_factory=Thresholds)
    screen: ScreenLimits = field(default_factory=ScreenLimits)
    keys: dict = field(default_factory=dict)


def load_settings() -> Settings:
    """Load defaults, overlaid by config.toml if present."""
    s = Settings()
    cfg_path = ROOT / "config.toml"
    if cfg_path.exists():
        data = tomllib.loads(cfg_path.read_text())
        srv = data.get("server", {})
        s.host = srv.get("host", s.host)
        s.port = int(srv.get("port", s.port))
        th = data.get("thresholds", {})
        s.thresholds = Thresholds(
            min_acres=float(th.get("min_acres", s.thresholds.min_acres)),
            max_slope_pct=float(th.get("max_slope_pct", s.thresholds.max_slope_pct)),
            sfha_fail_pct=float(th.get("sfha_fail_pct", s.thresholds.sfha_fail_pct)),
        )
        sc = data.get("screen", {})
        s.screen = ScreenLimits(
            max_parcels=int(sc.get("max_parcels", s.screen.max_parcels)),
            slope_grid=int(sc.get("slope_grid", s.screen.slope_grid)),
            concurrency=int(sc.get("concurrency", s.screen.concurrency)),
        )
        s.keys = data.get("keys", {})
    return s


SETTINGS = load_settings()
