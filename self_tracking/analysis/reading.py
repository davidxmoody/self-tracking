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
from self_tracking.dirs import diary_dir
import pandas as pd
import plotly.express as px


# %% [markdown]
# ## Load data


# %% jupyter={"source_hidden": true}
reading = pd.read_table(diary_dir / "data/kindle.tsv", parse_dates=["date"])

listening = pd.read_table(diary_dir / "data/audible.tsv", parse_dates=["date"])

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
    yaxis_title="Duration (hours)",
    legend_title="Audiobook",
)
fig


# %% [markdown]
# ## Books


# %% jupyter={"source_hidden": true}
def assign_periods(group, max_gap_days=90):
    gaps = group["date"].diff().dt.days.fillna(0)
    return (gaps > max_gap_days).cumsum()


df["period"] = df.groupby("title", group_keys=False).apply(
    assign_periods, include_groups=False
)

grouped = (
    df.groupby(["title", "period"])
    .agg(duration=("duration", "sum"), start=("date", "min"), end=("date", "max"))
    .reset_index()
)

grouped = grouped.loc[grouped.duration > 3]

grouped["quarter"] = grouped.end.dt.to_period("Q").dt.start_time


# %% jupyter={"source_hidden": true}
fig = px.bar(
    grouped,
    x="duration",
    y="quarter",
    text="title",
    color="title",
    color_discrete_sequence=px.colors.qualitative.Alphabet,
)
fig.update_traces(textposition="inside")
fig.update_layout(
    autosize=False,
    width=1100,
    height=800,
    xaxis_title="Duration (hours)",
    yaxis_title=None,
    showlegend=False,
)
fig
