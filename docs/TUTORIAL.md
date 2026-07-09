# Tutorial — A guided walkthrough

This walks you through a real search from start to finish:
**"Find land that could work for a self-storage facility within 15 miles of
Guerneville."** By the end you'll know what every control and column means.

If the tool isn't running yet, do the [Quick Start](QUICKSTART.md) first, then
come back. Open **<http://127.0.0.1:8000>** in your browser.

---

## The screen at a glance

- **Left panel** — your controls, in four numbered steps (Area, Criteria,
  Manual listings, Export).
- **Map (top right)** — a dashed **circle** shows your search area around
  Guerneville. After a search, parcels appear as colored shapes.
- **Results table (bottom right)** — one row per parcel, sorted best-first.

There's also a **❓ Help & Guide** button at the top of the panel for a quick
refresher any time.

---

## Step 1 — Set your search area

Under **"1 · Area — radius from Guerneville"**:

- Drag the **Radius** slider, or type an exact number in **"Exact miles."**
  Start with **15**.
- The dashed circle on the map updates to match. Everything the tool screens is
  inside that circle, centered on downtown Guerneville.

> Why a circle from Guerneville? That's the target market. Most land in this area
> is **unincorporated county**, which the tool has full zoning data for. Cities
> like Santa Rosa are handled separately (see [FAQ](FAQ.md)).

---

## Step 2 — Set your criteria

Under **"2 · Criteria":**

| Control | What it does | Suggested start |
|---|---|---|
| **Min parcel size (acres)** | Ignores parcels smaller than this. Storage facilities usually want a few usable acres. | **1** |
| **Max mean slope (%)** | Parcels steeper than this **fail** — storage needs flat, buildable pads. | **8** |
| **Vacant land only** | Only looks at unbuilt land (from the county assessor). Untick to also include any parcel you've tagged with a listing. | ✅ on |
| **Commercial / industrial vacant land only** | Narrows to land the assessor classifies as commercial/industrial — the most likely to be storage-zoned. Big speed-up. | ✅ on |
| **Unincorporated county only** | Skips parcels inside city limits (where zoning isn't mapped yet). | ✅ on |
| **Fail on ANY FEMA flood-zone overlap (strict)** | If on, a parcel fails if *any* part touches a FEMA flood zone. If off, flood is noted but doesn't automatically fail. Given Guerneville's flooding, leave it on. | ✅ on |

---

## Step 3 — Run the search

Click the blue **Screen parcels** button.

- The status line shows a spinner and *"Querying parcels, flood, zoning &
  slope…"*.
- **The first run takes ~1–2½ minutes** — it's checking each parcel against live
  FEMA, county, and USGS servers. Later runs are faster (results are cached).
- When it finishes, the status line reads something like *"149 candidate parcels
  in radius · screened 120."* (It checks the largest, most promising parcels
  first and caps the number per run to stay quick and polite to the servers.)

---

## Step 4 — Read your results

The list shows **only the parcels worth a look** — 🟢 **PASS** and 🟡 **REVIEW**.
Parcels that fail a hard filter are hidden and only tallied (e.g. "107 screened
out"). Want to see them? Click **show** next to that count — the failed parcels
appear with the reason in the **Notes** column, and a **FAIL** filter pill lets
you isolate them; click **hide** to collapse again. If nothing qualifies you'll
see **"No qualifying parcels found"** — widen the radius or loosen the criteria.
At the top, the counts (**All / PASS / REVIEW**) double as filters.

### The two verdicts you'll see

| Badge | Meaning |
|---|---|
| 🟢 **PASS** | Clears every hard filter: **not** in a flood zone, zoning **permits** storage (with solid confidence), flat enough, and big enough. Your best leads. |
| 🟡 **REVIEW** | Promising but needs a human look — usually because storage is allowed but the zoning read needs confirming, the parcel spans several zones, or slope data was missing. |

Parcels that are **screened out** (🔴 would-be FAIL) are ones ruled out by a hard
filter — in a flood zone, zoning doesn't allow storage, too steep, or too small.
They aren't listed, just counted.

The **Score** (0–100) ranks the qualifying parcels — higher is better. It rewards
being flood-free, cleanly zoned, flat, larger, and vacant/for-sale.

### The columns

| Column | What it tells you |
|---|---|
| **Status** | PASS or REVIEW (screened-out parcels aren't listed). |
| **Score** | Overall suitability rank (higher = better). |
| **APN** | Assessor's Parcel Number — the county's unique ID for the parcel. |
| **Address** | Situs address if the county has one (`0 NONE` means unaddressed land — normal for vacant parcels). |
| **Juris.** | Jurisdiction — "Unincorp." = unincorporated county. |
| **Zoning** | The zoning district that drives the verdict (e.g. `M2`, `MP`, `C3`). |
| **Permit** | How storage is allowed there: **by-right** (allowed outright), **use-permit** (needs a conditional Use Permit), **no**, or **verify**. |
| **FEMA** | The flood zone(s) touching the parcel. `X` = outside the mapped flood risk area (good). `AE`, `A`, `AO`… = in a Special Flood Hazard Area (bad). |
| **%SFHA** | How much of the parcel is inside a flood hazard area. `0` is what you want. |
| **Slope%** | Average slope across the parcel. Lower = flatter = easier to build. |
| **Acres** | Parcel size. |
| **Vacant/Use** | What the county says is on it (e.g. "Vacant commercial"). |
| **List $** | Shows a price/link if you've tagged the parcel with a listing (Step 6). |
| **Notes** | Plain-English reasons behind the verdict (e.g. "In FEMA SFHA (100% of parcel)"). |
| **Links** | Quick jumps — see below. |

### The links in each row

- **county** — the county's official parcel/assessor record.
- **map** — Google Maps at the parcel's location (great for a quick aerial look).
- **FEMA** — FEMA's official flood map viewer for that spot.
- **code** — the exact Sonoma County zoning code section behind the permit call,
  so you (or your planner) can verify it.

### Sorting and filtering

- **Filter by verdict:** the colored counts above the table — **All / PASS /
  REVIEW / FAIL** — are clickable. Click **PASS** to show only your best leads on
  both the table and the map; click it again, click **All**, or use **✕ clear**
  (or the **Filter:** label) to show everything.
- **Sort any column:** click a column header (APN, Acres, Slope%, Score, etc.) to
  sort by it; a small ▲/▼ shows the direction, and clicking again reverses it.
  Handy for "largest parcels first" (Acres) or "flattest first" (Slope%).
- **Export follows what you see:** if you've filtered to PASS, the Excel/CSV
  export contains just those rows. Clear the filter first to export everything.

---

## Step 5 — Focus on the best leads

Click a **PASS** row. The parcel highlights on the map and the view pans to it.
In our 15-mile example, the top hits are flat, flood-free industrial parcels
(zones `M2` / `MP`) out near the county airport — for instance a ~12-acre M2
parcel on Westwind Blvd. Use the **map** link to eyeball the site and the
**county** link to check ownership and details.

Hover over the map shapes too — green = PASS, amber = REVIEW, red = FAIL.

---

## Step 6 — Tag a for-sale listing (optional)

The tool finds *vacant* land whether or not it's listed. If you know a parcel is
actively for sale (from LoopNet, Crexi, LandWatch, etc.), tell the tool so it
shows up with a price and link:

1. Under **"3 · Manual listings,"** paste the parcel's **APN**, the **listing
   URL**, and optionally a **price**.
2. Click **Add listing**. It's saved on your computer and will attach to that
   parcel on your next screen (even if the parcel isn't vacant).

---

## Step 7 — Export

After any search, click **Excel (.xlsx)** or **CSV** under **"4 · Export."** You
get the full results table — colored by status in Excel — to share, sort, or
drop into your own analysis.

---

## Step 8 — Try a second pass

Now experiment:

- **Widen the net:** untick *"Commercial / industrial vacant land only"* to
  include vacant land the assessor classifies as residential/other that might
  still sit in a storage-friendly zone. (More parcels = a slower run.)
- **Loosen flood:** untick *"Fail on ANY FEMA flood-zone overlap"* to *see*
  flood-touched parcels (marked, not auto-failed) — useful if you're weighing a
  parcel that's only partly in the fringe.
- **Change slope or size:** raise **Max slope** to see more marginal terrain, or
  raise **Min acres** to focus on larger sites.

Each change re-runs against live data, so give it a moment.

---

## What to do with a promising parcel

A PASS is a **starting point, not a green light.** Before getting serious, you
(or your team) still need to check things the tool can't: wetlands, road access,
utilities, environmental history, title, exact permit conditions, and current
for-sale status. Confirm zoning and flood with **Permit Sonoma (707-565-1900)**
and FEMA. See the [FAQ](FAQ.md) for the full list of what's and isn't covered.
