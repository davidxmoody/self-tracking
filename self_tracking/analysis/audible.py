# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     notebook_metadata_filter: language_info
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: self_tracking
#     language: python
#     name: self_tracking
#   language_info:
#     codemirror_mode:
#       name: ipython
#       version: 3
#     file_extension: .py
#     mimetype: text/x-python
#     name: python
#     nbconvert_exporter: python
#     pygments_lexer: ipython3
#     version: 3.13.2
# ---

# %% [markdown]
# ## Imports


# %% jupyter={"source_hidden": true}
from os.path import expandvars
import zipfile
import pandas as pd
from pathlib import Path
import plotly.express as px


# %% [markdown]
# ## Load Audible data


# %% jupyter={"source_hidden": true}
zip_path = expandvars("$DIARY_DIR/misc/2025-04-29-audible-export.zip")

dfs = {}

with zipfile.ZipFile(zip_path, "r") as zf:
    for file_info in zf.infolist():
        if not file_info.is_dir():
            if file_info.filename.endswith(".csv"):
                with zf.open(file_info.filename) as file:
                    df = pd.read_csv(file)
                    name = (
                        Path(file_info.filename)
                        .stem.removeprefix("Digital.")
                        .removeprefix("Audible.")
                        .removeprefix("Audible.")  # Removes duplicate prefixes
                        .removesuffix(".csv")  # Removes duplicate suffixes
                    )
                    dfs[name] = df

pd.DataFrame(
    {"name": name, "rows": df.shape[0], "cols": df.shape[1]} for name, df in dfs.items()
)


# %% jupyter={"source_hidden": true}
listening = dfs["Listening"].dropna()
listening = pd.DataFrame(
    {
        "date": pd.to_datetime(listening["Start Date"]),
        "duration": listening["Event Duration Milliseconds"] / (1000 * 60 * 60),
        "title": listening["Product Name"],
    }
)
listening = listening.groupby(["date", "title"]).sum().reset_index()
listening = listening.loc[listening.groupby("title").duration.transform("sum") > 2]
listening["title"] = (
    listening["title"]
    .str.replace(r"\(.*?\)", "", regex=True)
    .str.replace(r":.*$", "", regex=True)
    .str.strip()
    .str.replace(r", Book \d$", "", regex=True)
)
listening


# %% [markdown]
# ## Yearly listening time


# %% jupyter={"source_hidden": true}
fig = px.bar(listening.groupby(pd.Grouper(key="date", freq="YS")).duration.sum())
fig.update_layout(
    autosize=False,
    width=1100,
    height=350,
    xaxis_title="Year",
    yaxis_title="Listening time (hours)",
    showlegend=False,
)
fig


# %% [markdown]
# ## Books by year


# %% jupyter={"source_hidden": true}
listening_grouped = (
    listening.groupby([pd.Grouper(key="date", freq="QS"), "title"])
    .duration.sum()
    .reset_index()
    .query("duration > 2")
)
fig = px.bar(listening_grouped, x="date", y="duration", color="title")
fig.update_layout(
    autosize=False,
    width=1100,
    height=600,
    xaxis_title="Date",
    yaxis_title="Listening time (hours)",
)
fig
