"""FastAPI app: serves the single-page UI and the screening API."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__, listings as listings_store
from .config import (
    COMMUNITIES, SETTINGS, Thresholds, WEB_DIR,
    GUERNEVILLE_CENTER, DEFAULT_RADIUS_MILES, MAX_RADIUS_MILES,
)
from .export import to_csv, to_xlsx
from .pipeline import screen_area

app = FastAPI(title="Storage Screener", version=__version__)


# --- request models ----------------------------------------------------------
class ScreenRequest(BaseModel):
    bbox: list[float] | None = None
    community: str | None = None
    center: list[float] | None = None       # [lon, lat]
    radius_miles: float | None = None
    min_acres: float | None = None
    max_slope_pct: float | None = None
    sfha_fail_pct: float | None = None
    only_vacant: bool = True
    commercial_only: bool = False
    unincorporated_only: bool = True


class ListingRequest(BaseModel):
    apn: str
    url: str | None = None
    price: str | None = None
    status: str | None = "For sale"
    note: str | None = None


class ExportRequest(BaseModel):
    results: list[dict]
    format: str = "xlsx"


# --- API ---------------------------------------------------------------------
@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/config")
def get_config() -> dict:
    t = SETTINGS.thresholds
    return {
        "communities": COMMUNITIES,
        "guerneville_center": list(GUERNEVILLE_CENTER),
        "default_radius_miles": DEFAULT_RADIUS_MILES,
        "max_radius_miles": MAX_RADIUS_MILES,
        "defaults": {
            "min_acres": t.min_acres,
            "max_slope_pct": t.max_slope_pct,
            "sfha_fail_pct": t.sfha_fail_pct,
        },
        "max_parcels": SETTINGS.screen.max_parcels,
        "listings": listings_store.load(),
    }


@app.post("/api/screen")
async def screen(req: ScreenRequest) -> dict:
    th = SETTINGS.thresholds
    thresholds = Thresholds(
        min_acres=req.min_acres if req.min_acres is not None else th.min_acres,
        max_slope_pct=req.max_slope_pct if req.max_slope_pct is not None else th.max_slope_pct,
        sfha_fail_pct=req.sfha_fail_pct if req.sfha_fail_pct is not None else th.sfha_fail_pct,
    )

    center = None
    radius = None
    bbox = req.bbox
    if req.center and req.radius_miles:
        if len(req.center) != 2:
            raise HTTPException(400, "center must be [lon, lat].")
        radius = min(float(req.radius_miles), MAX_RADIUS_MILES)
        center = (req.center[0], req.center[1])
        bbox = None
    elif bbox is None and req.community:
        bbox = COMMUNITIES.get(req.community)

    if center is None and (not bbox or len(bbox) != 4):
        raise HTTPException(400, "Provide center+radius_miles, a bbox, or a community.")

    return await screen_area(
        thresholds=thresholds, bbox=bbox, center=center, radius_miles=radius,
        only_vacant=req.only_vacant, commercial_only=req.commercial_only,
        unincorporated_only=req.unincorporated_only,
    )


@app.get("/api/listings")
def get_listings() -> list[dict]:
    return listings_store.load()


@app.post("/api/listings")
def add_listing(req: ListingRequest) -> list[dict]:
    return listings_store.add(req.model_dump())


@app.delete("/api/listings/{apn}")
def delete_listing(apn: str) -> list[dict]:
    return listings_store.delete(apn)


@app.post("/api/export")
def export(req: ExportRequest) -> Response:
    if req.format == "csv":
        data = to_csv(req.results)
        return Response(
            data, media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=storage_screen.csv"},
        )
    data = to_xlsx(req.results)
    return Response(
        data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=storage_screen.xlsx"},
    )


# --- static frontend (mounted last so /api/* wins) ---------------------------
@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


app.mount("/", StaticFiles(directory=WEB_DIR), name="web")
