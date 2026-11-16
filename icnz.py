"""
Fetch the Insurance Council of New Zealand (ICNZ) "Cost of natural disasters" table,
sum flood and storm losses per year, and plot them.

The "Cost of natural disasters (csv)" button on the ICNZ page is generated in the
browser by the DataTables plugin from the HTML table already embedded in the page
(#table_1), so there is no CSV file URL to download. We read that same table here.

Classification logic is ported from ICNZ_file_converter.py:
  - earthquake events are dropped;
  - an event is a flood if "flood"/"Flood" appears in its Event or Categories text;
  - of the remainder, an event is a storm if "storm"/"Storm" appears in either;
  - everything else (e.g. cyclones without "storm" in the text, tornadoes, fires) is not counted.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

import lxml.html
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402
from matplotlib.ticker import AutoMinorLocator, MultipleLocator  # noqa: E402

ICNZ_URL = "https://www.icnz.org.nz/industry/cost-of-natural-disasters/"
USER_AGENT = "Mozilla/5.0 (compatible; icnz-insured-losses-plot/1.0)"

FLOOD_COLOUR = "#6699FF"
STORM_COLOUR = "#FF6600"

# Standard column names used internally.
COLS = ["Date", "Event", "Categories", "Cost ($m)", "Inflation adjusted ($m)"]
# ICNZ has renamed the inflation-adjusted column at least once.
INFLATION_ALIASES = ["Inflation Adjusted CPI ($m)", "Inflation adjusted cost ($m)"]


def _standardise(raw: pd.DataFrame) -> pd.DataFrame:
    """Map a raw ICNZ table (scraped or CSV) onto COLS with clean types."""
    raw = raw.rename(columns=lambda c: str(c).strip())
    infl_col = next((c for c in INFLATION_ALIASES if c in raw.columns), None)
    if infl_col is None:
        raise ValueError(f"No inflation-adjusted column found in {list(raw.columns)}")
    df = raw[["Date", "Event", "Categories", "Cost ($m)", infl_col]].copy()
    df.columns = COLS
    for c in ["Date", "Event", "Categories"]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    for c in ["Cost ($m)", "Inflation adjusted ($m)"]:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace(",", "").str.strip().replace({"": None, "nan": None}),
            errors="coerce",
        )
    # Where no inflation-adjusted value is given, fall back to the nominal cost.
    df["Inflation adjusted ($m)"] = df["Inflation adjusted ($m)"].fillna(df["Cost ($m)"])
    df = df[df["Event"] != ""].copy()  # the page pads the table with empty rows
    df["Year"] = df["Date"].str.split().str[0].astype(int)
    return df.reset_index(drop=True)


def fetch_events(url: str = ICNZ_URL, timeout: float = 30) -> pd.DataFrame:
    """Download the ICNZ page and return the event table (one row per event)."""
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
    resp.raise_for_status()
    # Pass bytes so lxml takes the character encoding from the page itself.
    doc = lxml.html.fromstring(resp.content)
    tables = doc.xpath('//table[@id="table_1"]')
    if not tables:
        raise ValueError("Could not find the ICNZ event table (#table_1) on the page; "
                         "the page layout may have changed.")
    table = tables[0]
    header = [th.text_content().strip() for th in table.xpath("./thead/tr/th")]
    rows = [[td.text_content().strip() for td in tr.xpath("./td")][: len(header)]
            for tr in table.xpath("./tbody/tr")]
    raw = pd.DataFrame(rows, columns=header).loc[:, ~pd.Index(header).duplicated()]
    return _standardise(raw)


def read_events_csv(path_or_buffer) -> pd.DataFrame:
    """Read a CSV exported with the button on the ICNZ page."""
    return _standardise(pd.read_csv(path_or_buffer, dtype=str))


def classify(events: pd.DataFrame) -> pd.DataFrame:
    """Add a 'Type' column: 'Flood', 'Storm', 'Earthquake', 'Annual total' or 'Not counted'."""
    ev = events.copy()
    text = ev["Event"] + " " + ev["Categories"]
    is_total = ev["Event"].str.fullmatch(r"(?i)annual total")
    is_quake = ev["Event"].str.contains("earthquake", case=False)
    is_flood = text.str.contains("flood|Flood")
    is_storm = text.str.contains("storm|Storm")
    ev["Type"] = np.select(
        [is_total, is_quake, is_flood, is_storm],
        ["Annual total", "Earthquake", "Flood", "Storm"],
        default="Not counted",
    )
    return ev


def summarise(events: pd.DataFrame) -> pd.DataFrame:
    """Sum inflation-adjusted losses per year for floods and storms."""
    ev = classify(events)
    ev = ev[ev["Type"].isin(["Flood", "Storm"])]
    out = (ev.pivot_table(index="Year", columns="Type", values="Inflation adjusted ($m)",
                          aggfunc="sum")
             .reindex(columns=["Flood", "Storm"])
             .rename(columns={"Flood": "floods ($m)", "Storm": "storms ($m)"}))
    out.index.name = "Date"
    out.columns.name = None
    return out.sort_index()


def plot_losses(summary: pd.DataFrame, start_year: int | None = None,
                partial_year: int | None = None):
    """Stacked bar chart of flood and storm losses, in the style of the Grapher figure."""
    s = summary.fillna(0.0)
    if start_year is not None:
        s = s[s.index >= start_year]
    years = s.index.to_numpy()
    floods = s["floods ($m)"].to_numpy()
    storms = s["storms ($m)"].to_numpy()

    fig, ax = plt.subplots(figsize=(10, 6.8), dpi=150)
    ax.bar(years, floods, width=1.0, color=FLOOD_COLOUR, label="Floods")
    ax.bar(years, storms, width=1.0, bottom=floods, color=STORM_COLOUR, label="Storms")
    if partial_year is not None and partial_year in s.index:
        i = list(years).index(partial_year)
        top = floods[i] + storms[i]
        ax.bar(years[i], top, width=1.0, fill=False, hatch="///", edgecolor="white",
               linewidth=0)
        ax.annotate("year\nto date", (years[i], top), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom", fontsize=9)

    x0 = start_year if start_year is not None else years.min() - 1
    ax.set_xlim(x0, years.max() + 1)
    ax.set_ylim(0, (floods + storms).max() * 1.03)
    ax.xaxis.set_major_locator(MultipleLocator(5))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    ax.yaxis.set_minor_locator(AutoMinorLocator(5))
    ax.tick_params(which="both", direction="in", top=True, right=True, labelsize=12)
    ax.tick_params(which="major", length=8)
    ax.tick_params(which="minor", length=4)
    ax.set_xlabel("Year", fontweight="bold", fontsize=15)
    ax.set_ylabel("Insurance related losses (inflation adjusted $M)", fontweight="bold",
                  fontsize=15)
    ax.legend(loc="upper left", frameon=False, fontsize=14, borderaxespad=1.5)
    fig.tight_layout()
    return fig


def fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    return buf.getvalue()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
