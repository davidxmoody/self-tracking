from self_tracking.dirs import diary_dir, projects_dir
import subprocess
from typing import Any

import pandas as pd
import numpy as np
from yaspin import yaspin

import self_tracking.data as d


# %%
weekly: Any = {"rule": "W-Mon", "closed": "left", "label": "left"}


def write_layer(series, category: str, name: str) -> int:
    file = diary_dir / f"layers/{category}/{name}.tsv"
    file.parent.mkdir(parents=True, exist_ok=True)
    old_contents = file.read_text() if file.exists() else None

    new_contents = (
        series.where(lambda x: x > 0)
        .dropna()
        .rename("value")
        .to_csv(sep="\t", float_format="%.4f")
    )

    has_changed = old_contents != new_contents

    if has_changed:
        file.write_text(new_contents)

    return int(has_changed)


def write_layers(table, category: str) -> int:
    return sum(write_layer(table[name], category, name) for name in table.columns)


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

    return write_layers(streaks_pivot, "streaks")


# %%
def atracker_layers():
    atracker = d.atracker(start_date=None).resample(**weekly).sum()
    return write_layers(atracker, "atracker")


# %%
def workout_layers():
    workouts = d.workouts().reset_index()
    workouts["date"] = (
        workouts.start.dt.tz_convert(None).dt.to_period("W").dt.start_time
    )

    workouts_pivot = pd.pivot_table(
        workouts, index="date", columns="type", values="duration", aggfunc="sum"
    )

    return write_layers(workouts_pivot, "workouts")


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
    return write_layer(layer, "misc", "holidays")


# %%
def git_layers():
    count = 0
    repos = projects_dir.glob("*/.git")
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

            count += write_layer(layer, "git", repo.parent.name)

    return count


# %%
def main():
    with yaspin(text="Layers") as spinner:
        count = 0
        count += streaks_layers()
        count += atracker_layers()
        count += workout_layers()
        count += misc_layers()
        count += git_layers()
        spinner.text += f" ({count} layers)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
