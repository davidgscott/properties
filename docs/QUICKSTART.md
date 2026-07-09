# Quick Start

**Storage Screener** finds land that could work for a self-storage facility in
and around **Guerneville, California**. It checks each parcel for four things —
zoning, flood risk, whether it's vacant, and how flat it is — and shows the
results on a map and in a table you can export to Excel.

This guide gets you from zero to your first results. No coding needed — you'll
copy and paste a few commands. Budget about **15 minutes** the first time.

> New to the terms? See the [FAQ](FAQ.md) for plain-English explanations of
> zoning, flood zones, slope, and "APN." For a click-by-click walkthrough once
> it's running, see the [Tutorial](TUTORIAL.md).

---

## What you need

- A **Mac or Windows** computer.
- **Python 3.11 or newer** (free — we'll install it below).
- An **internet connection** (the tool pulls live data from government websites).
- It's **free** to run and needs **no accounts or API keys**.

---

## Step 1 — Install Python (one time)

**Check if you already have it.** Open a terminal:
- **Mac:** press `Cmd + Space`, type **Terminal**, hit Enter.
- **Windows:** press the Start key, type **PowerShell**, hit Enter.

Type this and press Enter:

```bash
python3 --version
```
(On Windows, try `python --version`.)

If you see **`Python 3.11`** or higher, skip to Step 2. If you see an error or an
older version:

- **Mac / Windows:** go to <https://www.python.org/downloads/> and click the big
  "Download Python" button. Run the installer.
  **On Windows, check the box that says "Add Python to PATH"** before clicking
  Install — this matters.
- Close and reopen your terminal, then run the version check again.

---

## Step 2 — Get the tool's files

**Option A — Download a ZIP (easiest, no extra tools):**
1. Go to the project page: <https://github.com/davidgscott/properties>
2. Click the green **`Code`** button ▸ **Download ZIP**.
3. Unzip it (double-click on Mac; right-click ▸ Extract All on Windows). You'll
   get a folder named `properties` (or `properties-main`).

**Option B — Use git (if you have it):**
```bash
git clone https://github.com/davidgscott/properties.git
```

---

## Step 3 — Open the folder in your terminal

In the terminal, type `cd ` (with a space) and then drag the `properties` folder
onto the terminal window and press Enter. It will look like:

```bash
cd /Users/you/Downloads/properties
```

Tip: run `ls` (Mac) or `dir` (Windows) — you should see files like `run.py` and
`requirements.txt`. That confirms you're in the right place.

---

## Step 4 — Install the tool's building blocks (one time)

```bash
python3 -m pip install -r requirements.txt
```
(Windows: use `python` instead of `python3`.)

This downloads the free libraries the tool uses. It takes a minute or two and
only needs to be done once. A "successfully installed…" message means you're set.

---

## Step 5 — Run it

```bash
python3 run.py
```
(Windows: `python run.py`.)

You'll see a message like *"Storage Screener running at http://127.0.0.1:8000"*
and your web browser should open automatically. If it doesn't, open your browser
and go to:

**<http://127.0.0.1:8000>**

That's the tool. 🎉

---

## Step 6 — Your first screen

1. In the left panel, leave the **Radius** at **15 miles** (the dashed circle on
   the map is your search area, centered on Guerneville).
2. Under **Criteria**, tick **"Commercial / industrial vacant land only"** and
   leave **"Unincorporated county only"** ticked.
3. Click the blue **Screen parcels** button.
4. **Wait about 1–2 minutes.** It's checking flood, zoning, and slope for each
   parcel live — the first run is the slow one. When it finishes, green **PASS**
   rows appear at the top of the table and as shapes on the map.

Click any row to highlight that parcel on the map, use the **county / map / FEMA
/ code** links in each row, and click **Excel (.xlsx)** to download the list.

The [Tutorial](TUTORIAL.md) explains what every column and color means.

---

## Stopping and restarting

- **To stop the tool:** click the terminal window and press **`Ctrl + C`**.
- **To start it again later:** open a terminal, `cd` into the `properties`
  folder (Step 3), and run `python3 run.py` (Step 5). You only do Steps 1, 2,
  and 4 once.

---

## Troubleshooting

**"python3: command not found" (or "python is not recognized")**
Python isn't installed or wasn't added to your PATH. Redo Step 1. On Windows,
reinstall Python and be sure to check **"Add Python to PATH."** Try `python`
instead of `python3` (or vice-versa).

**"Address already in use" / port 8000 busy**
The tool is probably already running in another terminal window. Either use that
one, or stop it with `Ctrl + C` and run again. (Advanced: you can change the port
by copying `config.example.toml` to `config.toml` and editing the `port` value.)

**The first screen is slow / seems stuck**
That's normal — a wide radius checks many parcels against live government servers
and can take 1–2½ minutes the first time. Later runs are faster because results
are cached. Watch the status line under the button; it shows progress.

**The map is blank / gray**
The map's background tiles come from OpenStreetMap and need internet. Check your
connection. The parcel results and table still work even if the background is
slow to load.

**"No candidate parcels" / empty results**
Try a **larger radius**, a **smaller "Min parcel size,"** or **untick
"Commercial / industrial vacant land only"** to widen the search. Right around
downtown Guerneville most land is residential, steep, or in the floodplain, so
the good candidates tend to be several miles out.

**Something else?**
Open the **❓ Help & Guide** button inside the tool, or see the full
[FAQ](FAQ.md).
