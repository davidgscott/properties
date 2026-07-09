"""Scoring: combine flood / zoning / slope / size / status into a verdict.

Status:
  FAIL   — a hard disqualifier: inside a FEMA SFHA, zoning explicitly disallows
           storage, slope too steep, or below minimum size.
  REVIEW — passes hard filters but has an unknown that needs a human: zoning not
           mapped (city or unmapped code), conditional-use path, slope data
           missing, or low-confidence zoning mapping.
  PASS   — outside SFHA, storage permitted (by-right or conditional), slope under
           the ceiling, meets size.

`score` (0-100) ranks survivors for the table; failed parcels keep a score for
sorting but are labeled FAIL.
"""
from __future__ import annotations

from ..config import Thresholds


def score_parcel(*, flood: dict, zoning_verdict: dict, slope: dict,
                 acres: float | None, vacant: bool, listed: bool,
                 th: Thresholds) -> dict:
    reasons: list[str] = []
    hard_fail = False

    # --- Flood (central filter) ---------------------------------------------
    sfha_pct = flood.get("sfha_pct") or 0.0
    if flood.get("in_sfha") and sfha_pct > th.sfha_fail_pct:
        hard_fail = True
        fw = " incl. FLOODWAY" if flood.get("floodway") else ""
        reasons.append(f"In FEMA SFHA ({sfha_pct}% of parcel, zones "
                       f"{','.join(flood.get('zones', [])) or '?'}{fw})")

    # --- Zoning --------------------------------------------------------------
    permitted = zoning_verdict.get("permitted")
    ptype = zoning_verdict.get("permit_type")
    if permitted is False:
        hard_fail = True
        reasons.append(f"Zoning {zoning_verdict.get('zone') or '?'} does not permit storage")
    elif permitted is None:
        reasons.append("Zoning permit status unknown — verify manually")
    elif ptype == "conditional":
        reasons.append("Storage allowed only with a Use Permit (conditional)")
    if permitted and zoning_verdict.get("confidence") == "low":
        reasons.append("Low-confidence zoning mapping — verify")

    # --- Slope ---------------------------------------------------------------
    mean_slope = slope.get("mean_pct")
    if mean_slope is None:
        reasons.append("Slope data unavailable")
    elif mean_slope > th.max_slope_pct:
        hard_fail = True
        reasons.append(f"Too steep (mean {mean_slope}% > {th.max_slope_pct}%)")

    # --- Size ----------------------------------------------------------------
    if acres is not None and acres < th.min_acres:
        hard_fail = True
        reasons.append(f"Below min size ({acres} ac < {th.min_acres} ac)")

    # --- Status --------------------------------------------------------------
    if hard_fail:
        status = "FAIL"
    elif permitted is None or mean_slope is None or ptype == "conditional" \
            or zoning_verdict.get("confidence") == "low":
        status = "REVIEW"
    else:
        status = "PASS"

    # --- Score (for ranking) -------------------------------------------------
    score = 0.0
    # Flood: clear = strong signal.
    score += 35 if not flood.get("in_sfha") else 0
    # Zoning path.
    score += {"by-right": 25, "conditional": 18}.get(ptype, 0) if permitted else 0
    if permitted is None:
        score += 8
    # Slope: flatter is better (up to 20 pts).
    if mean_slope is not None:
        score += max(0.0, 20 * (1 - min(mean_slope, th.max_slope_pct) / th.max_slope_pct))
    # Vacancy / listing.
    if vacant:
        score += 12
    if listed:
        score += 8

    return {
        "status": status,
        "score": round(score, 1),
        "reasons": reasons,
    }
