from glob import glob
from os import makedirs
from os.path import basename, dirname, expandvars
import subprocess
from typing import Any

import pandas as pd
import numpy as np
from yaspin import yaspin

import self_tracking.data as d


# %%
weekly: Any = {"rule": "W-Mon", "closed": "left", "label": "left"}


def write_layer(series, category: str, name: str):
    filepath = expandvars(f"$DIARY_DIR/layers/{category}/{name}.tsv")
    makedirs(dirname(filepath), exist_ok=True)
    series.where(lambda x: x > 0).dropna().rename("value").to_csv(
        filepath, sep="\t", float_format="%.4f"
    )


def write_layers(table, category: str):
    for name in table.columns:
        write_layer(table[name], category, name)


# %%
def streaks_layers():
    streaks = d.streaks()
    streaks["score"] = streaks.value.map({"completed": 1, "skipped": 0.7, "missed": -3})

    streaks_pivot = (
        streaks.pivot_table(values="score", index="date", columns="name")
        .resample(**weekly)
        .mean()
        .clip(0, 1)
        .replace(0, np.nan)
    )

    write_layers(streaks_pivot, "streaks")


# %%
def atracker_layers():
    atracker = d.atracker(start_date=None).resample(**weekly).sum()
    write_layers(atracker, "atracker")


# %%
def workout_layers():
    workouts = d.workouts().reset_index()
    workouts["date"] = (
        workouts.start.dt.tz_convert(None).dt.to_period("W-Mon").dt.start_time
    )

    workouts_pivot = pd.pivot_table(
        workouts, index="date", columns="type", values="duration", aggfunc="sum"
    )

    write_layers(workouts_pivot, "workouts")


# %%
def misc_layers():
    layer = (
        d.holidays()
        .rename(columns={"end": "date"})
        .set_index("date")
        .duration.dt.days.resample(**weekly)
        .sum()
        .astype("Int64")
    )
    write_layer(layer, "misc", "holidays")


# %%
def git_layers():
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
            capture_output=True,
            text=True,
        ).stdout.splitlines()

        if commit_dates:
            layer = (
                pd.DataFrame({"date": pd.to_datetime(commit_dates)})
                .groupby("date")
                .size()
                .resample(**weekly)
                .sum()
                .astype("Int64")
            )

            write_layer(layer, "git", basename(dirname(repo)))


# %%
def main():
    with yaspin(text="Layers") as spinner:
        streaks_layers()
        atracker_layers()
        workout_layers()
        misc_layers()
        git_layers()
        spinner.ok("✔")


if __name__ == "__main__":
    main()
