from glob import glob
from os import makedirs
from os.path import basename, dirname, expandvars
import subprocess
from typing import Any

import pandas as pd
from yaspin import yaspin

import self_tracking.data as d


# %%
weekly: Any = {"rule": "W-Mon", "closed": "left", "label": "left"}


def stringify_index(series: pd.Series):
    return series.rename(lambda x: str(x.date()))


def write_layer(series, category: str, name: str):
    filepath = expandvars(f"$DIARY_DIR/layers/{category}/{name}.json")
    makedirs(dirname(filepath), exist_ok=True)
    stringify_index(series[series > 0]).dropna().clip(0, 1).round(2).to_json(
        filepath, indent=2
    )


# %%
def streaks_layers():
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
def atracker_layers():
    atracker = d.atracker().resample(**weekly).sum()

    for category in atracker.columns:
        non_zero = atracker[category][atracker[category] > 0.0]
        limit = non_zero.quantile(0.75)
        layer = non_zero.apply(lambda x: x / limit)
        write_layer(layer, "atracker", category)


# %%
def workout_layers():
    workouts = d.workouts()

    for workout_type in workouts.type.unique():
        durations = (
            workouts.query(f"type == '{workout_type}'")
            .duration.resample(**weekly)
            .sum()
        )
        layer = durations / durations.quantile(0.95)
        write_layer(layer, "workouts", workout_type)


# %%
def misc_layers():
    holidays_layer = (
        d.holidays().set_index("end").duration.dt.days.resample(**weekly).sum() / 5
    )
    write_layer(holidays_layer, "misc", "holidays")


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
            commit_dates_layer = (
                pd.DataFrame({"date": pd.to_datetime(commit_dates)})
                .groupby("date")
                .size()
                .resample(**weekly)
                .sum()
                / 7
            ) ** 0.5

            write_layer(commit_dates_layer, "git", basename(dirname(repo)))


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
