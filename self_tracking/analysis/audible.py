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
import pandas as pd
import plotly.express as px


# %% [markdown]
# ## Load Audible data


# %% jupyter={"source_hidden": true}
listening = pd.read_table(
    expandvars("$DIARY_DIR/data/audible.tsv"), parse_dates=["date"]
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
