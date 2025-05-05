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
import pandas as pd
import plotly.express as px


# %% [markdown]
# ## Load data


# %% jupyter={"source_hidden": true}
reading = pd.read_table(expandvars("$DIARY_DIR/data/kindle.tsv"), parse_dates=["date"])

listening = pd.read_table(
    expandvars("$DIARY_DIR/data/audible.tsv"), parse_dates=["date"]
)

reading["audio"] = False
listening["audio"] = True

df = pd.concat([reading, listening]).sort_values("date").reset_index(drop=True)


# %% [markdown]
# ## Formats


# %% jupyter={"source_hidden": true}
fig = px.bar(
    df.groupby([pd.Grouper(key="date", freq="QS"), "audio"])
    .duration.sum()
    .reset_index(),
    x="date",
    y="duration",
    color="audio",
)
fig.update_layout(
    autosize=False,
    width=1100,
    height=350,
    xaxis_title="Date",
    yaxis_title="Listening time (hours)",
    legend_title="Audiobook",
)
fig


# %% [markdown]
# ## Books


# %% jupyter={"source_hidden": true}
fig = px.bar(
    df.groupby([pd.Grouper(key="date", freq="QS"), "title"])
    .duration.sum()
    .reset_index()
    .query("duration > 2")
    .sort_values("date", ascending=False),
    x="date",
    y="duration",
    color="title",
)
fig.update_layout(
    autosize=False,
    width=1100,
    height=600,
    xaxis_title="Date",
    yaxis_title="Listening time (hours)",
    legend_title="Title",
)
fig
