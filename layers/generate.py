# %% Imports

from os import makedirs
from os.path import dirname, expandvars

import pandas as pd


# %% Helpers


def read_data(name: str, index_col: str | None = "date"):
    return pd.read_table(
        expandvars(f"$DIARY_DIR/data/{name}.tsv"),
        parse_dates=["date"],
        index_col=index_col,
    )


def resample_weekly(series: pd.Series):
    return series.resample("W-Mon", closed="left", label="left")


def stringify_index(series: pd.Series):
    return (
        series.reset_index()
        .astype({series.index.name: "str"})
        .set_index(series.index.name)[series.name]
    )


def write_layer(series, category: str, name: str):
    filepath = expandvars(f"$DIARY_DIR/layers/{category}/{name}.json")
    makedirs(dirname(filepath), exist_ok=True)
    stringify_index(series).clip(0, 1).round(2).to_json(filepath, indent=2)


# %% Streaks


def score_week(values):
    if "completed" not in values.values:
        return 0
    score = max(0, values.map({"completed": 1, "skipped": 0.9, "missed": -2}).mean())
    return score * 0.8 + 0.2


streaks = read_data("streaks", index_col=None)

for name in streaks.name.unique():
    values = streaks.query("name == @name").set_index("date").value
    weekly = resample_weekly(values).agg(score_week)
    write_layer(weekly, "streaks", name)


# %% Running

running = read_data("running").distance
running_weekly = resample_weekly(running).sum()
write_layer((running_weekly**0.5) / 5, "fitness", "running")
