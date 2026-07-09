/* Storage Screener frontend — Leaflet map + results table + manual listings. */
"use strict";

const STATUS_COLOR = { PASS: "#1a7f37", REVIEW: "#c69214", FAIL: "#b42318" };
const FEMA_NFHL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer";

let map, parcelLayer, femaLayer, radiusCircle, centerMarker;
let lastResults = [], selectedApn = null, statusFilter = null;
let sortCol = null, sortDir = 1;         // table sort state (1 asc, -1 desc)
let showScreenedOut = false;             // reveal ruled-out (FAIL) parcels
let cfg = { defaults: {}, guerneville_center: [-122.9958, 38.5021], max_radius_miles: 20 };
const MILES_TO_M = 1609.344;

// ---- init -------------------------------------------------------------------
async function init() {
  map = L.map("map", { zoomControl: true }).setView([38.5021, -122.9958], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: "© OpenStreetMap",
  }).addTo(map);

  // FEMA flood overlay — show ONLY the high-risk Special Flood Hazard Areas
  // (layer 28, SFHA_TF='T'), i.e. the zones that actually disqualify a parcel.
  // Rendering the whole NFHL service made the map look blanketed in flood.
  femaLayer = L.esri.dynamicMapLayer({
    url: FEMA_NFHL, opacity: 0.4, layers: [28], layerDefs: { 28: "SFHA_TF = 'T'" },
  }).addTo(map);
  parcelLayer = L.geoJSON(null, {
    style: styleFor,
    onEachFeature: (f, layer) => layer.on("click", () => selectRow(f.properties.apn)),
  }).addTo(map);
  radiusCircle = L.circle([38.5021, -122.9958], { radius: 15 * MILES_TO_M,
    color: "#1f6feb", weight: 2, fill: false, dashArray: "6 6" }).addTo(map);

  L.control.layers(null, {
    "FEMA high-risk flood (SFHA)": femaLayer, "Screened parcels": parcelLayer,
    "Search radius": radiusCircle,
  }, { collapsed: false }).addTo(map);
  addLegend();

  cfg = await (await fetch("/api/config")).json();
  const [clon, clat] = cfg.guerneville_center;
  radiusCircle.setLatLng([clat, clon]);
  centerMarker = L.circleMarker([clat, clon], { radius: 5, color: "#1f6feb",
    fillColor: "#1f6feb", fillOpacity: 1 }).addTo(map).bindTooltip("Guerneville");

  const r = cfg.default_radius_miles ?? 15, maxR = cfg.max_radius_miles ?? 20;
  ["radius-slider", "radius-num"].forEach(id => {
    document.getElementById(id).max = maxR;
    document.getElementById(id).value = r;
  });
  document.getElementById("min-acres").value = cfg.defaults.min_acres ?? 1;
  document.getElementById("max-slope").value = cfg.defaults.max_slope_pct ?? 8;
  syncLabels();
  updateRadius();
  renderListings(cfg.listings || []);
  wire();
}

function wire() {
  document.getElementById("radius-slider").addEventListener("input", e => {
    document.getElementById("radius-num").value = e.target.value; updateRadius();
  });
  document.getElementById("radius-num").addEventListener("input", e => {
    document.getElementById("radius-slider").value = e.target.value; updateRadius();
  });
  document.getElementById("min-acres").addEventListener("input", syncLabels);
  document.getElementById("max-slope").addEventListener("input", syncLabels);
  document.getElementById("screen-btn").addEventListener("click", runScreen);
  document.getElementById("add-listing").addEventListener("click", addListing);
  document.getElementById("export-xlsx").addEventListener("click", () => doExport("xlsx"));
  document.getElementById("export-csv").addEventListener("click", () => doExport("csv"));

  // Info tooltips: show on hover (CSS); toggle on tap/click for touch devices,
  // without activating the label's checkbox/slider.
  const closeTips = () => document.querySelectorAll(".tip.open")
    .forEach(t => t.classList.remove("open"));
  document.querySelectorAll(".tip").forEach(t => {
    t.addEventListener("click", e => {
      e.preventDefault(); e.stopPropagation();
      const open = t.classList.contains("open");
      closeTips();
      if (!open) t.classList.add("open");
    });
  });
  document.addEventListener("click", closeTips);

  // Help modal open/close.
  const modal = document.getElementById("help-modal");
  const showHelp = () => { modal.hidden = false; };
  const hideHelp = () => { modal.hidden = true; };
  document.getElementById("help-btn").addEventListener("click", showHelp);
  document.getElementById("help-close").addEventListener("click", hideHelp);
  modal.addEventListener("click", e => { if (e.target === modal) hideHelp(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape") { hideHelp(); closeTips(); } });
}

// ---- area -------------------------------------------------------------------
function radiusMiles() {
  return parseFloat(document.getElementById("radius-num").value) || 15;
}
function updateRadius() {
  const mi = radiusMiles();
  radiusCircle.setRadius(mi * MILES_TO_M);
  map.fitBounds(radiusCircle.getBounds().pad(0.05));
  document.getElementById("radius-val").textContent = mi + " mi";
  document.getElementById("area-note").textContent =
    `Circle ≈ ${(Math.PI * mi * mi).toFixed(0)} sq mi centered on downtown Guerneville.`;
}
function syncLabels() {
  document.getElementById("acres-val").textContent =
    document.getElementById("min-acres").value + " ac";
  document.getElementById("slope-val").textContent =
    document.getElementById("max-slope").value + " %";
}

// ---- screen -----------------------------------------------------------------
async function runScreen() {
  const btn = document.getElementById("screen-btn");
  const line = document.getElementById("status-line");
  btn.disabled = true;
  line.innerHTML = `<span class="spinner"></span>Querying parcels, flood, zoning &amp; slope… ` +
    `(a wide radius can take a minute)`;
  try {
    const body = {
      center: cfg.guerneville_center,
      radius_miles: radiusMiles(),
      min_acres: parseFloat(document.getElementById("min-acres").value),
      max_slope_pct: parseFloat(document.getElementById("max-slope").value),
      sfha_fail_pct: document.getElementById("strict-flood").checked ? 0 : 100,
      only_vacant: document.getElementById("only-vacant").checked,
      commercial_only: document.getElementById("commercial-only").checked,
      unincorporated_only: document.getElementById("uninc-only").checked,
    };
    const res = await fetch("/api/screen", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    const data = await res.json();
    lastResults = data.results;
    renderResults();
    line.textContent = `${data.in_area} candidate parcels in radius · screened ${data.count}` +
      (data.truncated ? ` (capped at ${data.max_parcels}, largest first)` : "");
  } catch (e) {
    line.innerHTML = `<span style="color:var(--fail)">Error: ${e.message}</span>`;
  } finally {
    btn.disabled = false;
  }
}

function styleFor(f) {
  const c = STATUS_COLOR[f.properties.status] || "#888";
  const sel = f.properties.apn === selectedApn;
  return { color: c, weight: sel ? 3 : 1.5, fillColor: c,
    fillOpacity: sel ? 0.5 : 0.28 };
}

// Column definitions: label + a sort accessor (columns without one aren't sortable).
const COLUMNS = [
  { label: "Status", sort: r => ({ PASS: 0, REVIEW: 1, FAIL: 2 })[r.status] },
  { label: "Score", sort: r => r.score },
  { label: "APN", sort: r => r.apn || "" },
  { label: "Address", sort: r => r.address || "" },
  { label: "Juris.", sort: r => shortJuris(r.jurisdiction) || "" },
  { label: "Zoning", sort: r => r.zoning || "" },
  { label: "Permit", sort: r => permitLabel(r) },
  { label: "FEMA", sort: r => r.flood_zone || "" },
  { label: "%SFHA", sort: r => r.sfha_pct ?? 0 },
  { label: "Slope%", sort: r => r.slope_mean_pct ?? -1 },
  { label: "Acres", sort: r => r.acres ?? -1 },
  { label: "Vacant/Use", sort: r => r.vacant_category || "" },
  { label: "List $", sort: r => priceKey(r) },
  { label: "Notes" },
  { label: "Links" },
];

function priceKey(r) {
  if (r.list_price) { const n = Number(String(r.list_price).replace(/[^0-9.]/g, "")); if (n) return n; }
  return r.listed ? 0 : -1;
}

function renderResults() {
  statusFilter = null; sortCol = null; sortDir = 1; showScreenedOut = false;
  rerender();
  if (displayed().length) { try { map.fitBounds(parcelLayer.getBounds().pad(0.1)); } catch (e) {} }
}

// Rebuild the summary, table, and map for the current display state (used on a
// new screen and after toggling show/hide screened-out). Clears any filter.
function rerender() {
  statusFilter = null;
  renderSummary();
  renderTable();
  const n = displayed().length;
  document.getElementById("export-xlsx").disabled = !n;
  document.getElementById("export-csv").disabled = !n;
}

// Summary line: filter pills, the "N screened out · show/hide" toggle, empty state.
function renderSummary() {
  const summary = document.getElementById("summary");
  const c = { PASS: 0, REVIEW: 0, FAIL: 0 };
  lastResults.forEach(r => c[r.status]++);
  const qCount = c.PASS + c.REVIEW;

  const toggle = c.FAIL
    ? `<span class="screened-out">${c.FAIL} screened out · ` +
      `<a class="so-toggle" title="${showScreenedOut ? "Hide" : "Show"} the ruled-out parcels and why they failed">` +
      `${showScreenedOut ? "hide" : "show"}</a></span>`
    : "";

  if (qCount === 0 && !showScreenedOut) {
    summary.innerHTML =
      `<span class="empty-msg">No qualifying parcels found in this area.</span>` +
      `<span class="muted">Try a larger radius, or loosen the criteria (min size / max slope).</span>` +
      toggle;
  } else {
    let html =
      `<span class="filter-label" title="Show all">Filter:</span>` +
      `<span class="pill all" data-status="" title="Show all">All ${displayed().length}</span>` +
      `<span class="pill pass" data-status="PASS" title="Show only PASS">PASS ${c.PASS}</span>` +
      `<span class="pill review" data-status="REVIEW" title="Show only REVIEW">REVIEW ${c.REVIEW}</span>`;
    if (showScreenedOut)
      html += `<span class="pill fail" data-status="FAIL" title="Show only screened-out">FAIL ${c.FAIL}</span>`;
    html += `<span class="filter-clear" title="Clear filter">✕ clear</span>` + toggle;
    summary.innerHTML = html;

    const clear = () => { statusFilter = null; applyFilter(); };
    summary.querySelectorAll(".pill").forEach(p => {
      p.addEventListener("click", () => {
        const s = p.dataset.status || null;
        statusFilter = (statusFilter === s) ? null : s;   // click active pill = clear
        applyFilter();
      });
    });
    summary.querySelector(".filter-label").addEventListener("click", clear);
    summary.querySelector(".filter-clear").addEventListener("click", clear);
  }

  const t = summary.querySelector(".so-toggle");
  if (t) t.addEventListener("click", () => { showScreenedOut = !showScreenedOut; rerender(); });
}

// Build the header + rows for the current display set, or clear the table.
function renderTable() {
  if (!displayed().length) {
    document.querySelector("#results-table thead").innerHTML = "";
    document.querySelector("#results-table tbody").innerHTML = "";
    drawParcels();
  } else {
    renderHeader();
    renderRows();
  }
}

// Build the sortable header row.
function renderHeader() {
  const cells = COLUMNS.map((c, i) => {
    const sortable = !!c.sort;
    const arrow = sortCol === i ? (sortDir === 1 ? " ▲" : " ▼") : "";
    return `<th${sortable ? ` class="sortable" data-col="${i}"` : ""}>${c.label}${arrow}</th>`;
  }).join("");
  const thead = document.querySelector("#results-table thead");
  thead.innerHTML = "<tr>" + cells + "</tr>";
  thead.querySelectorAll("th.sortable").forEach(th =>
    th.addEventListener("click", () => setSort(+th.dataset.col)));
}

function setSort(i) {
  if (sortCol === i) { sortDir = -sortDir; }           // same column → toggle direction
  else {                                               // new column → sensible default
    sortCol = i;
    const sample = lastResults.length ? COLUMNS[i].sort(lastResults[0]) : "";
    sortDir = typeof sample === "number" ? -1 : 1;     // numbers high→low, text A→Z
  }
  renderHeader();
  renderRows();
}

// Parcels worth showing — PASS or REVIEW. FAIL parcels are screened out.
function qualifying() {
  return lastResults.filter(r => r.status !== "FAIL");
}

// The set currently on display: qualifying only, or everything when the user
// has clicked "show" screened-out.
function displayed() {
  return showScreenedOut ? lastResults : qualifying();
}

// Displayed results in the current sort order (falls back to server ranking).
function sortedResults() {
  const base = displayed();
  if (sortCol == null) return base;
  const acc = COLUMNS[sortCol].sort;
  return [...base].sort((a, b) => {
    const va = acc(a), vb = acc(b);
    if (typeof va === "number" && typeof vb === "number") return (va - vb) * sortDir;
    return String(va).localeCompare(String(vb)) * sortDir;
  });
}

// Results shown in the table/export: current sort order, then the status filter.
function visibleResults() {
  const base = sortedResults();
  return statusFilter ? base.filter(r => r.status === statusFilter) : base;
}

function rowHTML(r) {
  const s = r.status.toLowerCase();
  const price = r.list_price ? r.list_price : (r.listed ? "listed" : "");
  return `<td><span class="tag ${s}">${r.status}</span></td>` +
    `<td>${r.score}</td>` +
    `<td class="mono">${r.apn}</td>` +
    `<td>${esc(r.address)}</td>` +
    `<td>${esc(shortJuris(r.jurisdiction))}</td>` +
    `<td>${r.zoning || "—"}</td>` +
    `<td>${permitLabel(r)}</td>` +
    `<td>${r.flood_zone}</td>` +
    `<td>${r.sfha_pct ?? 0}</td>` +
    `<td>${r.slope_mean_pct ?? "—"}</td>` +
    `<td>${r.acres ?? "—"}</td>` +
    `<td>${esc(r.vacant_category || "")}</td>` +
    `<td>${r.listing_url ? `<a href="${r.listing_url}" target="_blank">${esc(price)}</a>` : esc(price)}</td>` +
    `<td class="reasons">${esc((r.reasons || []).join("; "))}</td>` +
    `<td>${linkCell(r)}</td>`;
}

// (Re)build the table body in the current sort order, then apply the filter.
function renderRows() {
  const tb = document.querySelector("#results-table tbody");
  tb.innerHTML = "";
  sortedResults().forEach(r => {
    const tr = document.createElement("tr");
    tr.dataset.apn = r.apn;
    tr.dataset.status = r.status;
    if (r.apn === selectedApn) tr.classList.add("sel");
    tr.innerHTML = rowHTML(r);
    tr.addEventListener("click", () => selectRow(r.apn));
    tb.appendChild(tr);
  });
  applyFilter();
}

// (Re)draw the parcels currently passing the filter onto the map.
function drawParcels() {
  parcelLayer.clearLayers();
  parcelLayer.addData({ type: "FeatureCollection", features: visibleResults().map(r => ({
    type: "Feature", properties: r, geometry: r.geometry,
  })) });
}

// Apply the active status filter to the pills, the table rows, and the map.
function applyFilter() {
  const summary = document.getElementById("summary");
  summary.classList.toggle("filtered", !!statusFilter);
  summary.querySelectorAll(".pill").forEach(p =>
    p.classList.toggle("active", (p.dataset.status || null) === statusFilter));
  document.querySelectorAll("#results-table tbody tr").forEach(tr => {
    tr.style.display = (!statusFilter || tr.dataset.status === statusFilter) ? "" : "none";
  });
  drawParcels();
}

function permitLabel(r) {
  if (r.storage_permitted === true)
    return r.permit_type === "by-right" ? "by-right" : "use-permit";
  if (r.storage_permitted === false) return "no";
  return "verify";
}
function shortJuris(j) {
  return j && j.startsWith("Unincorporated") ? "Unincorp." : j;
}
function linkCell(r) {
  const l = r.links || {};
  return `<a href="${l.county}" target="_blank">county</a> · ` +
    `<a href="${l.google_maps}" target="_blank">map</a> · ` +
    `<a href="${l.fema}" target="_blank">FEMA</a>` +
    (r.zoning_verify_url ? ` · <a href="${r.zoning_verify_url}" target="_blank">code</a>` : "");
}

function selectRow(apn) {
  selectedApn = apn;
  document.querySelectorAll("#results-table tbody tr").forEach(tr =>
    tr.classList.toggle("sel", tr.dataset.apn === apn));
  const tr = document.querySelector(`#results-table tbody tr[data-apn="${CSS.escape(apn)}"]`);
  if (tr) tr.scrollIntoView({ block: "nearest" });
  parcelLayer.setStyle(styleFor);
  const r = lastResults.find(x => x.apn === apn);
  if (r) map.panTo([r.lat, r.lon]);
}

// ---- listings ---------------------------------------------------------------
async function addListing() {
  const apn = document.getElementById("l-apn").value.trim();
  if (!apn) return;
  const body = {
    apn,
    url: document.getElementById("l-url").value.trim() || null,
    price: document.getElementById("l-price").value.trim() || null,
  };
  const items = await (await fetch("/api/listings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })).json();
  ["l-apn", "l-url", "l-price"].forEach(id => document.getElementById(id).value = "");
  renderListings(items);
}
async function delListing(apn) {
  renderListings(await (await fetch(`/api/listings/${encodeURIComponent(apn)}`,
    { method: "DELETE" })).json());
}
function renderListings(items) {
  const ul = document.getElementById("listing-list");
  ul.innerHTML = "";
  items.forEach(i => {
    const li = document.createElement("li");
    const label = i.url ? `<a href="${i.url}" target="_blank">${esc(i.apn)}</a>` : esc(i.apn);
    li.innerHTML = `<span>${label}${i.price ? " · " + esc(i.price) : ""}</span>` +
      `<button title="remove">✕</button>`;
    li.querySelector("button").addEventListener("click", () => delListing(i.apn));
    ul.appendChild(li);
  });
}

// ---- export -----------------------------------------------------------------
async function doExport(fmt) {
  const res = await fetch("/api/export", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ results: visibleResults(), format: fmt }),
  });
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `storage_screen.${fmt}`;
  a.click();
  URL.revokeObjectURL(a.href);
}

// ---- misc -------------------------------------------------------------------
function addLegend() {
  const lc = L.control({ position: "bottomleft" });
  lc.onAdd = () => {
    const d = L.DomUtil.create("div", "legend");
    d.innerHTML =
      `<i style="background:${STATUS_COLOR.PASS}"></i>Pass<br>` +
      `<i style="background:${STATUS_COLOR.REVIEW}"></i>Review<br>` +
      `<i style="background:${STATUS_COLOR.FAIL}"></i>Fail`;
    return d;
  };
  lc.addTo(map);
}
function esc(s) {
  return String(s ?? "").replace(/[&<>"]/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

init();
