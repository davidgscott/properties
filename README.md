# Storage Screener — Sonoma County

A locally-run tool that screens real-estate parcels for **self-storage
development** in and around **Guerneville, California**. It combines free,
authoritative government data into one map + table:

- **Zoning** — does the parcel's zone permit self-storage (by-right / conditional)?
- **FEMA flood** — is any of the parcel inside a Special Flood Hazard Area?
  (central filter — Guerneville floods off the Russian River)
- **Vacant / for-sale** — vacant land from county assessor use-codes, plus any
  listings you paste in
- **Slope** — is it flat-ish and buildable (USGS 3DEP elevation)?

Every parcel is scored **PASS / REVIEW / FAIL** with reasons, shown on a Leaflet
map over the live FEMA flood layer, and exportable to Excel/CSV.

> **Screening aid, not legal advice.** Confirm zoning and flood status with
> Permit Sonoma (707-565-1900) and FEMA before acting on any result.

## Quick start

```bash
pip install -r requirements.txt
python run.py                 # opens http://127.0.0.1:8000
```

No API keys are required — all four data domains use free public services.

1. Set the **radius** from downtown Guerneville (number box or slider, default
   15 mi) — the dashed circle on the map shows the search area.
2. Set **min acreage** and **max slope**; toggle *vacant-only*,
   *commercial/industrial only*, *unincorporated county only*, *strict flood*.
3. Click **Screen parcels**.
4. Optionally paste **listings** (APN + LoopNet/Crexi URL) to tag for-sale parcels.
5. **Export** the results to `.xlsx` / `.csv`.

The area is a **configurable-radius circle around Guerneville**. Because the
radius can cover tens of thousands of parcels, the vacant + size (+ optional
commercial/industrial and unincorporated-only) filters are pushed into the
parcel query server-side, so only the relevant few hundred candidates are
pulled; they're clipped to the circle, ranked largest-first, and capped before
enrichment. Example: a 15-mile radius with *commercial/industrial vacant,
unincorporated* yields ~150 candidates and surfaces flat, flood-free M2/M3/MP
industrial parcels near the county airport as the top prospects.

## Data sources (all verified live, free)

| Domain | Source | Endpoint |
|---|---|---|
| Parcels | Sonoma County GIS | `AGCOMMPublic/Sonoma_County_Parcels` |
| Zoning | Permit Sonoma base zoning | `Zoning_Area` (`DISTRICT`) — unincorporated county |
| Flood | FEMA NFHL Layer 28 + county F1 floodway | `hazards.fema.gov/.../NFHL/MapServer/28` |
| Slope | USGS 3DEP `getSamples` (+ EPQS fallback) | `3DEPElevation/ImageServer` |

## How screening works

`app/pipeline.py` orchestrates: query parcels in the area → prefilter on
size + vacancy → for each survivor concurrently resolve **jurisdiction, zoning
district, FEMA SFHA overlap %, and slope** → score. Only prefiltered parcels get
the expensive calls, and the count is capped for politeness (`config.toml`).

### Zoning rule engine (the crux)

`app/rules/zoning_lookup.yaml` maps `(jurisdiction, zone code) → permitted /
permit-type / confidence`, with a code-article link per entry. Unincorporated
Sonoma County is seeded (C3, M1–M3, MP as conditional-use candidates) at
**medium confidence** — the county code use-tables (Municode/eLaws) blocked
automated fetch, so **verify entries before relying on them**. Incorporated
cities are intentionally left unmapped (every city parcel → REVIEW) until their
use tables are added — see *Phase 2* below.

## Layout

```
app/
  config.py            endpoints + tunable thresholds (edit here if a URL moves)
  arcgis.py            async ArcGIS client + on-disk cache
  geometry.py          ArcGIS rings <-> shapely, overlap %, centroid
  sources/             parcels, zoning, flood, slope, jurisdiction
  rules/               storage_zoning.py + zoning_lookup.yaml + scoring.py
  pipeline.py          raw parcel -> scored candidate
  export.py            xlsx / csv
  main.py              FastAPI routes
web/                   index.html + app.js + app.css (Leaflet UI)
run.py                 python run.py
```

## Roadmap

- **Phase 1 (done):** Guerneville + unincorporated county — flood, county zoning,
  slope, vacant, export.
- **Phase 2 (done):** configurable-radius-from-Guerneville area mode with a
  server-side vacant/size/commercial/unincorporated prefilter so a wide radius
  stays tractable. Focused on unincorporated Sonoma County (the county zoning
  layer's coverage); incorporated cities are skipped by default.
- **Phase 3 (optional, paid):** Regrid normalized city zoning (to cover
  incorporated cities); BAREIS MLS feed (if licensed); ATTOM/Realtor listings
  API. Keys go in `config.toml` (git-ignored).

## Configuration

Copy `config.example.toml` → `config.toml` to override thresholds, the parcel
cap, or add optional paid-source keys. The free MVP needs none.
