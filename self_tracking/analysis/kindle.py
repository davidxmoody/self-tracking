# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Imports


# %% jupyter={"source_hidden": true}
from os.path import expandvars
import zipfile
import pandas as pd


# %% [markdown]
# ## Load Kindle data


# %% jupyter={"source_hidden": true}
zip_path = expandvars("$DIARY_DIR/misc/2025-04-24-kindle-export.zip")
filepaths = {
    "reading": "Kindle.ReadingInsights/datasets/Kindle.reading-insights-sessions_with_adjustments/Kindle.reading-insights-sessions_with_adjustments.csv",
    "whispersync": "Digital.Content.Whispersync/whispersync.csv",
}
dfs = {}

with zipfile.ZipFile(zip_path, "r") as zf:
    for name, filepath in filepaths.items():
        with zf.open(filepath) as file:
            dfs[name] = pd.read_csv(file)


# %%
reading = dfs["reading"]

reading["start"] = (
    pd.to_datetime(reading.start_time, format="ISO8601", utc=True)
    .dt.tz_convert("Europe/London")
    .dt.round("1s")
)

reading["duration"] = reading.total_reading_milliseconds / (1000 * 60 * 60)

whispersync = dfs["whispersync"]

book_titles = whispersync.drop_duplicates("ASIN").set_index("ASIN")["Product Name"]

reading["title"] = (
    reading.ASIN.map(book_titles)
    .fillna("Not Available")
    .str.replace(r"^Penguin Readers Level \d: ", "", regex=True)
    .str.replace(r" - Updated Edition", "", regex=True)
    .str.replace(r", The - .*", "", regex=True)
    .str.replace(r"\(.*?\)", "", regex=True)
    .str.replace(r":.*$", "", regex=True)
    .str.strip()
)

reading = reading.loc[reading.duration > (1 / 60)]
reading = reading[["start", "duration", "title"]]
reading = reading.sort_values("start").reset_index(drop=True)


# %%
reading.groupby(
    [pd.Grouper(key="start", freq="MS"), "title"]
).duration.sum().reset_index()


# %%
reading.groupby("title").start.apply(lambda x: x.diff().max()).sort_values()
