# FAQ — Data, reliability, and how to trust the results

Plain-English answers to the questions that come up most. New to the tool? Start
with the [Quick Start](QUICKSTART.md) and [Tutorial](TUTORIAL.md).

> **The one-sentence version:** this is a **screening aid** that combines free,
> official government data to shortlist parcels worth a closer look — it is
> **not** legal, engineering, or planning advice, and a "PASS" is a lead, not a
> guarantee.

---

## Where does the data come from?

Everything comes from **free, official public sources** — the same data the
county, FEMA, and USGS publish. No private or paid databases are used.

| What | Source | Who runs it | How fresh |
|---|---|---|---|
| **Parcels** (boundaries, size, address, assessor land-use) | Sonoma County parcel GIS (`Sonoma_County_Parcels`) | Sonoma County | Refreshed ~monthly from the assessor's roll |
| **Zoning** (which district a parcel is in) | Permit Sonoma base-zoning layer (`Zoning_Area`) | Sonoma County / Permit Sonoma | Maintained by the county; unincorporated areas |
| **Flood zones** | FEMA National Flood Hazard Layer (NFHL), plus the county's F1 Floodway overlay | FEMA (+ Sonoma County) | FEMA's live regulatory flood map |
| **Slope / elevation** | USGS 3DEP elevation (with EPQS as a backup) | U.S. Geological Survey | Best available, 1-meter LiDAR where flown over Sonoma |

The exact web addresses for each are in the project's `app/config.py`, and every
result row has a **FEMA** and **county** link so you can check the original
source for that specific parcel.

## How reliable and current is each source?

- **Flood (FEMA NFHL)** is the **authoritative regulatory** flood layer — it's
  what lenders and floodplain managers use. This is the most trustworthy piece.
  For a formal determination on a specific parcel, use the **FEMA** link in the
  row to pull the official map.
- **Parcels (county)** come straight from the assessor and are updated about
  monthly. Boundaries and sizes are reliable for screening; treat them as
  "good enough to shortlist," not a survey.
- **Zoning (county)** is the county's own layer. The *district* (e.g. `M2`) is
  reliable; whether that district *permits storage* is the tool's interpretation
  of the zoning code — see confidence below.
- **Slope (USGS)** uses high-quality elevation data (1-meter LiDAR where
  available). The slope number is a solid flat-vs-steep indicator; it does not
  account for gullies, drainage, or a specific building footprint.

## Is the data live or a snapshot?

**Live.** Each time you click *Screen parcels*, the tool queries these servers in
real time (and briefly caches answers so repeat runs are fast). You're always
seeing current published data — no stale copy bundled into the tool.

---

## What do PASS / REVIEW / FAIL mean?

- 🟢 **PASS** — clears every hard filter: not in a flood zone, zoning permits
  storage with **high confidence**, flat enough, and big enough.
- 🟡 **REVIEW** — promising but a human should confirm something: the zoning is
  permissive but the read needs verifying (**medium confidence**), the parcel
  spans several zones, or slope data was unavailable.
- 🔴 **FAIL** — ruled out by a hard filter (in a flood zone, zoning doesn't allow
  storage, too steep, or too small). The row's **Notes** say why.

The **Score** (0–100) just ranks parcels within those groups.

## What does the "confidence level" mean?

Confidence is about **one specific thing: how sure we are that the parcel's
zoning permits self-storage.** Zoning codes don't say "self-storage yes/no" in a
single field — you have to read the county's use tables. Here's how sure the tool
is for each zone, and why:

| Confidence | Zones | Why |
|---|---|---|
| **High** | **C3, MP, M2** | The Sonoma County code **explicitly** lists storage as permitted **by right** — e.g. C3 §26-34-010(v): *"Warehouses including mini-warehouses, moving and storage companies."* We read this directly from the code. |
| **Medium** | **M1, M3** | Storage is permitted **by right** via a broader "heavy commercial uses for which storage is necessary" clause (§26-46-010(d) / §26-50-010(d)) — a very reasonable reading, but not the literal word "warehouse," so it's worth confirming. |
| **Not allowed** | LC, C1, C2, CO, CR, AS, K, and all residential/agricultural zones | These districts don't list a storage/warehouse use. |
| **Unknown → REVIEW** | Incorporated-city zones, "Planned Community," or anything unmapped | Not in the tool's lookup, so it won't guess. |

Every zoning verdict links to the exact **code** section (the "code" link in each
row) so you or a planner can verify it. The full mapping lives in
`app/rules/zoning_lookup.yaml`.

**Important nuance:** "by-right" means storage doesn't need a special *use
permit* — but you still need Design Review, building permits, and to satisfy any
overlay (like a floodplain combining district). It's not "build without asking."

## Why is storage "by-right" here but I heard it needs a use permit?

Earlier drafts of this tool assumed storage was conditional (needs a use permit)
everywhere. When we read the **actual Chapter 26 use tables**, C3, MP, and M2
list it as permitted by right. That's why those show as PASS. M1 and M3 rely on a
broader clause, so they stay REVIEW until confirmed.

---

## How is "in a flood zone" decided?

The tool takes the parcel's shape and asks FEMA's flood layer which flood zones
it overlaps, then calculates **what percentage of the parcel** sits in a Special
Flood Hazard Area (zones A, AE, AO, AH, V, VE, etc.). With **strict flood** on
(the default), *any* overlap fails the parcel — appropriate for Guerneville,
where the Russian River floods regularly. It also flags the **floodway** (the
most dangerous part). `X` in the FEMA column means outside the mapped risk area.

## How is slope calculated?

The tool samples USGS elevation across a grid over the parcel and computes the
**average and maximum slope** as a percentage (rise over run). Under ~8% reads as
"flat-ish and buildable." It's a screening estimate, not a grading plan.

## How is "vacant" determined?

From the county assessor's **land-use code** (descriptions containing "vacant" or
"undeveloped") and a near-zero **improvement value** (meaning little or nothing is
built on it). A parcel can be "vacant" in the assessor's records even if there's
an old shed on it, so eyeball the **map** link.

---

## Why does it only cover unincorporated county? Where's Santa Rosa?

The county's zoning data covers **unincorporated** Sonoma County — which is most
of the Guerneville area and the tool's focus. Incorporated cities (Santa Rosa,
Windsor, Healdsburg, Sebastopol, etc.) each keep their **own** zoning, in their
own formats, and aren't mapped in the tool yet. With **"Unincorporated county
only"** ticked (the default), the tool skips them so you don't get parcels it
can't evaluate. Adding cities is on the roadmap (see below).

## What does the tool NOT check?

A PASS means a parcel clears the four automated filters — **not** that it's
buildable or available. Still up to you and your team:

- **Wetlands, creeks, riparian setbacks, and drainage**
- **Road access and frontage**
- **Utilities** (power, water, sewer/septic availability)
- **Environmental history / contamination**
- **Title, easements, and current ownership**
- **Exact permit conditions and design standards**
- **Whether it's actually for sale and at what price** (unless you tag a listing)
- **City zoning** (for parcels inside incorporated cities)

Treat the tool as the first filter that turns hundreds of parcels into a
handful worth real due diligence.

## Is this legal or planning advice?

**No.** It's an informational screening tool. Before acting on any parcel,
confirm zoning and permitting with **Permit Sonoma (707-565-1900)** and flood
status with **FEMA**, and involve the appropriate professionals.

---

## Practical questions

**How much does it cost to run?**
$0. Every data source is a free public service. There are no accounts, no API
keys, and nothing to subscribe to.

**Does it send my information anywhere?**
It only talks to the public government data servers (FEMA, county, USGS) to look
up parcels — the same sites you could visit yourself. Any listings you add are
saved **locally on your computer** (`app/data/listings.json`); nothing is uploaded.

**Why is the first search slow?**
A wide radius checks many parcels against several live servers, one after another
(politely). Expect ~1–2½ minutes for a 15-mile run the first time. Repeat runs
are faster because answers are cached. Narrowing the radius or ticking
"Commercial / industrial vacant land only" speeds it up a lot.

**Can it cover a different area or the cities later?**
Yes — the search center/radius and the zoning lookup are configurable, and adding
city zoning is a planned next step. Ask whoever set this up for you.

**Something looks wrong for a specific parcel.**
Data can lag reality (a recent split, rezoning, or new construction). Use the
**county**, **FEMA**, and **code** links in the row to check the official source,
and trust those over the tool for anything you're acting on.
