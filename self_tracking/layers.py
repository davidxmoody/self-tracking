from glob import glob
from os import makedirs
from os.path import basename, dirname, expandvars
import subprocess
from typing import Any

import pandas as pd

import self_tracking.data as d


# %%
weekly: Any = {"rule": "W-Mon", "closed": "left", "label": "left"}


def stringify_index(series: pd.Series):
    return (
        series.reset_index()
        .astype({series.index.name: "str"})
        .set_index(series.index.name)[series.name or 0]
    )


def write_layer(series, category: str, name: str):
    filepath = expandvars(f"$DIARY_DIR/layers/{category}/{name}.json")
    makedirs(dirname(filepath), exist_ok=True)
    stringify_index(series[series > 0]).dropna().clip(0, 1).round(2).to_json(
        filepath, indent=2
    )


# %%
streaks = d.streaks()
streaks["score"] = streaks.value.map({"completed": 1, "skipped": 0.7, "missed": -3})

streaks_pivot = (
    streaks.pivot_table(values="score", index="date", columns="name")
    .resample(**weekly)
    .mean()
)

for streak in streaks_pivot.columns:
    write_layer(streaks_pivot[streak], "streaks", streak)


# %%
atracker = d.atracker().resample(**weekly).sum()

for category in atracker.columns:
    non_zero = atracker[category][atracker[category] > pd.to_timedelta(0)]
    limit = non_zero.quantile(0.75)
    layer = non_zero.apply(lambda x: x / limit)
    write_layer(layer, "atracker", category)


# %%
running_layer = (d.running().distance.resample(**weekly).sum() ** 0.5) / 5
write_layer(running_layer, "fitness", "running")


# %%
cycling_indoor_layer = d.cycling_indoor().calories.resample(**weekly).sum() / 2000
write_layer(cycling_indoor_layer, "fitness", "cycling-indoor")

cycling_outdoor_layer = d.cycling_outdoor().calories.resample(**weekly).sum() / 2000
write_layer(cycling_outdoor_layer, "fitness", "cycling-outdoor")


# %%
strength = d.strength().drop_duplicates("date").set_index("date").title
strength_layer = strength.resample(**weekly).size() / 4
write_layer(strength_layer, "fitness", "strength")


# %%
meditation = d.meditation().duration
meditation_layer = meditation.resample(**weekly).sum().dt.total_seconds() / (120 * 60)
write_layer(meditation_layer, "misc", "meditation")


# %%
climbing_layer = (d.climbing().place.resample(**weekly).size() / 3) ** 0.5
write_layer(climbing_layer, "fitness", "climbing")


# %%
holidays_layer = (
    d.holidays().set_index("end").duration.dt.days.resample(**weekly).sum() / 5
)
write_layer(holidays_layer, "misc", "holidays")


# %%
repos = glob(expandvars("$P_DIR/*/.git"))
my_name = subprocess.run(
    ["git", "config", "user.name"], check=True, capture_output=True, text=True
).stdout.strip()

for repo in repos:
    commit_dates = subprocess.run(
        [
            "git",
            f"--git-dir={repo}",
            "log",
            "--date=short",
            "--pretty=tformat:%cd",
            f"--author={my_name}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    commit_dates_layer = (
        pd.DataFrame({"date": pd.to_datetime(commit_dates)})
        .groupby("date")
        .size()
        .resample(**weekly)
        .sum()
        / 7
    ) ** 0.5

    write_layer(commit_dates_layer, "git", basename(dirname(repo)))
