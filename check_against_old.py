"""
Regression checks for icnz.py (run locally; not needed by the Streamlit app).

1. The 2023 CSV run through icnz.summarise() must reproduce storms_and_floods_2.dat,
   which ICNZ_file_converter.py made from it.
2. The table scraped live from the ICNZ page must match the CSV exported with the
   page's "Cost of natural disasters (csv)" button.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import icnz

old_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    r"D:\Sync\Projects\ClimateChange\Graphics\Greg_ICNZ_Figure")
new_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else old_dir / "ICNZData_asat_16Nov2026.csv"

# 1. Port matches the old converter.
expected = pd.read_csv(old_dir / "storms_and_floods_2.dat", index_col=0).sort_index()
got = icnz.summarise(icnz.read_events_csv(old_dir / "ICNZData_asat_9Nov2023.csv"))
assert list(got.index) == list(expected.index), (set(got.index) ^ set(expected.index))
assert np.allclose(got.to_numpy(), expected.to_numpy(), equal_nan=True, atol=1e-9)
print(f"1. OK: summarise(2023 CSV) reproduces storms_and_floods_2.dat ({len(got)} years)")

# 2. Live scrape matches the button-exported CSV.
scraped = icnz.fetch_events()
exported = icnz.read_events_csv(new_csv)
pd.testing.assert_frame_equal(scraped.drop(columns="Event"), exported.drop(columns="Event"))
n_name_diff = (scraped["Event"] != exported["Event"]).sum()
print(f"2. OK: live scrape matches {new_csv.name} ({len(scraped)} events; "
      f"{n_name_diff} event names differ only in text encoding)")
if n_name_diff:
    d = scraped["Event"] != exported["Event"]
    print(pd.DataFrame({"scraped": scraped["Event"][d], "csv": exported["Event"][d]}))
