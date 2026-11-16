"""
Streamlit page: New Zealand insured losses from floods and storms (ICNZ data).

Run locally with:
    streamlit run icnz_streamlit_app.py
"""

import streamlit as st

import icnz

st.set_page_config(page_title="NZ insured losses: floods and storms", layout="centered")


@st.cache_resource
def store() -> dict:
    """One shared holder for the last successfully fetched data (survives reruns)."""
    return {"events": None, "fetched": None, "source": None}


def refresh(holder: dict) -> None:
    """Fetch from ICNZ; replace the stored data only if the fetch succeeds."""
    try:
        with st.spinner("Downloading the latest data from ICNZ..."):
            events = icnz.fetch_events()
    except Exception as exc:  # network failure, page layout change, etc.
        st.warning(f"Could not refresh from ICNZ ({exc}). "
                   + ("Showing the data fetched earlier." if holder["events"] is not None
                      else "You can upload a CSV exported from the ICNZ page below."))
        return
    holder.update(events=events, fetched=icnz.now_utc(), source="ICNZ web page")


holder = store()

st.title("Insured losses from floods and storms in New Zealand")

if st.button("Refresh", type="primary", help="Download the latest data from ICNZ"):
    refresh(holder)
elif holder["events"] is None:
    refresh(holder)

with st.expander("No connection to ICNZ? Upload a CSV instead"):
    upload = st.file_uploader("CSV from the 'Cost of natural disasters (csv)' button",
                              type="csv")
    if upload is not None:
        holder.update(events=icnz.read_events_csv(upload), fetched=icnz.now_utc(),
                      source=f"uploaded file {upload.name}")

events = holder["events"]
if events is None:
    st.stop()

summary = icnz.summarise(events)
first, last = int(summary.index.min()), int(summary.index.max())
start_year = st.slider("Start year", first, last - 1, min(max(1995, first), last - 1))

latest_event = events.loc[events["Year"] == last, "Date"].iloc[0] if last in events["Year"].values else ""
partial_year = last if icnz.now_utc().year == last else None

fig = icnz.plot_losses(summary, start_year=start_year, partial_year=partial_year)
st.pyplot(fig)

st.caption(
    "Source: Insurance Council of New Zealand, "
    f"[Cost of natural disasters]({icnz.ICNZ_URL}). "
    "Losses are inflation adjusted (CPI) and summed per calendar year. "
    "An event counts as a flood if 'flood' appears in its name or category; "
    "otherwise as a storm if 'storm' does. Earthquakes and other events are excluded."
    + (f" {partial_year} is year to date (latest event: {latest_event})." if partial_year else "")
    + f"  \nData from {holder['source']}, retrieved "
    f"{holder['fetched'].strftime('%Y-%m-%d %H:%M UTC')}."
)

col1, col2 = st.columns(2)
col1.download_button("Download plot (PNG)", icnz.fig_to_png(fig),
                     file_name="nz_flood_storm_insured_losses.png", mime="image/png")
col2.download_button("Download yearly totals (CSV)", summary.to_csv().encode(),
                     file_name="storms_and_floods.csv", mime="text/csv")

with st.expander("Event-level data and how each event was classified"):
    classified = icnz.classify(events)
    st.dataframe(
        classified[["Date", "Event", "Categories", "Inflation adjusted ($m)", "Type"]],
        hide_index=True, width="stretch",
    )
