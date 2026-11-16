# NZ insured losses from floods and storms (ICNZ data)

A small [Streamlit](https://github.com/streamlit/streamlit) app that downloads the latest
Insurance Council of New Zealand (ICNZ) "Cost of natural disasters" data, sums the
inflation-adjusted insured losses from **floods** and **storms** per calendar year, and draws
a stacked bar chart. It has a **Refresh** button to pull the latest data from ICNZ on demand.

- **Live app:** <https://nz-insured-losses.streamlit.app/>
- **Embedded on:** the Bodeker Scientific web page (Google Sites), under Data
- **Code:** <https://github.com/GBodeker/icnz_insured_losses> (public, under Greg's personal GitHub account)
- **Data source:** <https://www.icnz.org.nz/industry/cost-of-natural-disasters/>
- **Created:** 16 November 2026, with Claude Code

---

## Why this exists

The flood/storm insured-losses figure gets used regularly in talks and funding proposals
(e.g. the 2026/27 MBIE HELM proposal). Previously it was made by hand in three steps:

1. Download the CSV from the ICNZ web page (the "Cost of natural disasters (csv)" button).
2. Run `D:\gitcode\python\users\gb_scripts\General\ICNZ_file_converter.py` on it to produce
   `storms_and_floods_2.dat` (yearly flood and storm totals).
3. Drag that file into Grapher to draw the plot.

The working files for that old workflow are in
`D:\Sync\Projects\ClimateChange\Graphics\Greg_ICNZ_Figure`.

This app does all three steps in one place, on a public web page, using matplotlib
instead of Grapher.

---

## Files

| File | What it is |
|---|---|
| `icnz_streamlit_app.py` | The Streamlit page (user interface only). This is the app's entry point. |
| `icnz.py` | All the real work: fetching the ICNZ table, classifying events, yearly sums, the matplotlib plot. Has no Streamlit code, so it can be imported and used from any script. |
| `check_against_old.py` | Regression checks (see [Verification](#verification)). Not used by the app. |
| `requirements.txt` | Packages Streamlit Community Cloud installs when it builds the app. |
| `.gitignore` | Keeps `.venv/`, `__pycache__/` and `*.png` out of the repo. |

---

## How the data are obtained (important, non-obvious)

**There is no CSV file to download.** The "Cost of natural disasters (csv)" button on the
ICNZ page links to `#`. The page uses the WordPress *wpDataTables* plugin, and the button is a
DataTables `csvHtml5` export: the browser builds the CSV on the fly from an HTML table that is
already embedded in the page. So `icnz.fetch_events()` downloads the page HTML and reads that
table (`<table id="table_1">`) directly with lxml. The result was checked to be identical to the
CSV the button produces (see [Verification](#verification)).

Things learned about the table along the way:

- **`pandas.read_html` does not work** on this page. Each event row contains a nested
  "More info" table (breakdown by claim type), which confuses it. Hence the explicit lxml parsing
  of `table_1`'s own `thead`/`tbody` rows.
- **The table is padded with empty rows** (441 rows, about 241 real events as of Nov 2026). Rows
  with no event name are dropped.
- **The `Year` column is garbled** on the web page (e.g. `2.026`, thousands-separator
  formatting). The year is taken from the first word of the `Date` column instead, as the old
  converter did.
- **ICNZ renamed a column** between Nov 2023 and Nov 2026: `Inflation adjusted cost ($m)` became
  `Inflation Adjusted CPI ($m)`. The old converter breaks on new downloads because of this.
  `icnz.py` accepts either name (`INFLATION_ALIASES`).
- **Where no inflation-adjusted value is given**, the nominal `Cost ($m)` is used (as in the old
  converter).
- **"Annual total" rows** exist from 2019 onwards. They sum that year's events and are dated
  1 January of the *following* year. They must not be counted (double counting, and in the wrong
  year). They are classified as `Annual total` and excluded explicitly.
- **The `Categories` column is only filled in from about 2020 onwards.** Earlier events can only
  be classified from keywords in the event name.

---

## How events are classified (a deliberate choice)

The rules are a faithful port of `ICNZ_file_converter.py` (`icnz.classify()`):

1. "Annual total" rows: excluded.
2. Event name contains "earthquake" (any case): excluded.
3. "flood" or "Flood" appears in the event name or categories: **Flood**.
4. Otherwise, "storm" or "Storm" appears (this includes "Hailstorm", "Windstorm",
   "Snowstorm", "Thunderstorm"): **Storm**.
5. Everything else: **Not counted**.

**Consequence:** several weather events are *not* counted. As of 16 Nov 2026, 43 events since
1995, about NZ$1.05 bn inflation adjusted, including Cyclone Debbie remnants (2017, $119m),
the Kaitaia tornado (2009, $105m), "Severe weather including tornadoes" (2018, $96m), Cyclone
Dovi (2022, category "Cyclone", $63m), Cyclone Fehi and Ex-Tropical Cyclone Gita (2018), and
other tornadoes, fires and "severe weather" events.

On 16 Nov 2026 we decided to **keep the original rules unchanged**, so the figure stays
consistent with earlier versions. To change this, edit `classify()` in `icnz.py` (for example,
add an "Other weather" class). The app's "Event-level data and how each event was classified"
panel shows how every event was classified.

---

## What the page shows

- A stacked bar chart of floods (blue `#6699FF`) and storms (orange `#FF6600`), styled after the
  old Grapher figure, on **one continuous y axis**. The old figure had a broken y axis
  (0–350 and 1000–3600); we chose not to do that for now.
- A **Start year** slider (default 1995; the data go back to 1968, when the Wahine storm
  dominates).
- The current calendar year, if present, is hatched and labelled **"year to date"**.
- A caption giving the source, the classification rule, and when the data were retrieved.
- Download buttons for the plot (PNG) and the yearly totals (CSV, the equivalent of the old
  `storms_and_floods_2.dat`).
- An **"upload a CSV instead"** fallback: if the ICNZ page can't be read, export the CSV with the
  button on the ICNZ page and upload it here.

### How Refresh works

The last successfully fetched data are held in memory, shared by all visitors
(`st.cache_resource`). The page fetches from ICNZ on first load after the app starts, and again
whenever **Refresh** is pressed. If a refresh fails (network error, page layout changed), the
previous data are kept and a warning is shown. When the free Community Cloud app goes to sleep
and wakes again, it starts fresh and fetches new data automatically.

---

## Expect these differences from the old Grapher figure

- **2023 is about $4.2 bn, not about $3.56 bn.** ICNZ has since revised the Auckland Anniversary
  floods and Cyclone Gabrielle figures (claims to 1 March 2024) and re-based the CPI adjustment.
  This is a data revision, not a bug.
- All earlier years also shift slightly, because the inflation adjustment is re-based each year.

---

## Running locally

Any Python 3.13 environment containing the packages in `requirements.txt` works. The app was
built and tested with Streamlit 1.67, pandas 3.1, matplotlib 3.11 and lxml.

With the existing conda environment (it needed matplotlib and lxml added):

```bash
conda activate bs-streamlit
conda install -c conda-forge matplotlib lxml   # one-off
cd D:\gitcode\icnz_insured_losses
streamlit run icnz_streamlit_app.py
```

Streamlit starts its own local web server and opens <http://localhost:8501>. No separate web
server (Apache, IIS, etc.) is needed.

(A `.venv` virtual environment was also created in this folder during development. It is not
needed if you use conda, is ignored by git, and can be deleted.)

The script can be named anything: `streamlit run anything.py` works. The only place the name
matters is the "Main file path" setting on Streamlit Community Cloud (below).

---

## Deployment (Streamlit Community Cloud)

Hosted free on [Streamlit Community Cloud](https://share.streamlit.io). This was chosen over
running it on Bodeker Scientific's Contabo VPS (which hosts the PMP tool) because there is no
server to maintain. The trade-off: the free app **goes to sleep** after a period with no
visitors, and the next visitor waits about 30 s (and may need to click a "wake up" button)
while it restarts. That is fine because Greg is the main user.

How it was set up:

1. The repo `GBodeker/icnz_insured_losses` was created on GitHub and the code pushed to it. From
   the command line, with the GitHub CLI logged in as `GBodeker`, that is:
   ```bash
   git init -b main && git add . && git commit -m "ICNZ flood and storm insured losses Streamlit app"
   gh repo create icnz_insured_losses --public --source=. --push
   ```
   The repo must be public, or Community Cloud must be given access to private repos.
2. At share.streamlit.io: **Continue with GitHub** → **Create app** →
   **Deploy a public app from GitHub**, with:
   - Repository: `GBodeker/icnz_insured_losses`, branch `main`
   - **Main file path: `icnz_streamlit_app.py`** (this must be typed in, because the default is
     `streamlit_app.py`)
   - App URL: `nz-insured-losses`
   - Advanced settings → Python version: 3.13
3. Community Cloud installs `requirements.txt` and starts the app.

**Updating the app:** edit the files, commit and `git push`. Community Cloud redeploys
automatically within a minute or two. App logs and settings (sharing, reboot, delete) are under
the app's ⋮ menu at share.streamlit.io.

---

## Embedding on the Bodeker Scientific web page (Google Sites)

In Google Sites: **Insert → Embed**, then either

- **By URL:** `https://nz-insured-losses.streamlit.app/?embed=true`, or
- **Embed code** (lets you set the height):
  ```html
  <iframe src="https://nz-insured-losses.streamlit.app/?embed=true"
          width="100%" height="1100" style="border:none;"></iframe>
  ```

**The `?embed=true` is essential.** Without it, the embed fails with
"share.streamlit.io redirected you too many times": inside an iframe, Community Cloud tries to
send the full app page through a redirect via share.streamlit.io, which loops. With
`?embed=true` it serves an embeddable version (with a small "Built with Streamlit" footer and a
"Fullscreen" link). This was confirmed by testing both forms side by side.

---

## Verification

`check_against_old.py` runs two checks:

1. **The port matches the old converter:** `ICNZData_asat_9Nov2023.csv` run through
   `icnz.summarise()` reproduces `storms_and_floods_2.dat` (made by `ICNZ_file_converter.py`)
   exactly, for all 43 years.
2. **The scrape matches the CSV button:** the table scraped live from the ICNZ page is identical
   to `ICNZData_asat_16Nov2026.csv`, exported with the button on the same day (241 events).

Both passed on 16 Nov 2026. To re-run (the defaults point at the files in
`D:\Sync\Projects\ClimateChange\Graphics\Greg_ICNZ_Figure`):

```bash
python check_against_old.py [old_data_dir] [freshly_exported_csv]
```

Check 1 is fixed history and should always pass. Check 2 needs a CSV exported from the ICNZ page
the same day, because ICNZ updates the data.

---

## Fixes relative to `ICNZ_file_converter.py`

- **Inflation fallback:** `data['...'].fillna(..., inplace=True)` on a single column silently does
  nothing under pandas 3 (copy-on-write). It is replaced by an explicit assignment.
- **Earthquake filter:** now case-insensitive. This doesn't change any results, since no
  earthquake row matches flood or storm.
- **Column rename:** handled (see above).
- **Annual totals:** excluded explicitly. The old script excluded them only by luck.
- **Output:** sorted by year. The old `.dat` was in merge order.

---

## If something breaks

- **"Could not refresh from ICNZ"** or **"Could not find the ICNZ event table (#table_1)"**:
  ICNZ has probably changed its page. Look at the page source, update `fetch_events()` in
  `icnz.py`, and use the CSV upload in the meantime.
- **New or renamed columns:** update `_standardise()` / `INFLATION_ALIASES` in `icnz.py`.
- **Build fails on Community Cloud:** check the log panel; usually a package or Python version
  problem. Pinning versions in `requirements.txt` (e.g. `pandas==3.1.1`) is the quick fix.

## Ideas not (yet) done

- A broken y axis, like the Grapher figure (code sketch in the original Claude conversation:
  two stacked subplots with `sharex=True`, the gap spines hidden, and diagonal break marks).
- An "Other weather" class (cyclones, tornadoes, "severe weather"); see the classification
  section.
- A scheduled GitHub Action that regenerates a static PNG weekly, as a fallback image for
  slides or for pages where an iframe is not wanted.
