from self_tracking.dirs import diary_dir

import pandas as pd
from yaspin import yaspin

import self_tracking.data as d


# %%
def write_layer(
    series, category: str, name: str, float_format: str | None = None
) -> int:
    file = diary_dir / f"layers/{category}/{name}.tsv"
    file.parent.mkdir(parents=True, exist_ok=True)
    old_contents = file.read_text() if file.exists() else None

    new_contents = (
        series[series > 0].rename("value").to_csv(sep="\t", float_format=float_format)
    )

    has_changed = old_contents != new_contents

    if has_changed:
        file.write_text(new_contents)

    return int(has_changed)


def write_layers(table, category: str, float_format: str | None = None) -> int:
    return sum(
        write_layer(table[name], category, name, float_format) for name in table.columns
    )


# %%
def streaks_layers():
    streaks = d.streaks()
    streaks["score"] = streaks.value.map({"completed": 1, "skipped": 0.3, "missed": 0})

    streaks_pivot = streaks.pivot_table(values="score", index="date", columns="name")

    return write_layers(streaks_pivot, "streaks", float_format="%.1f")


# %%
def atracker_layers():
    atracker = d.atracker(start_date=None)
    return write_layers(atracker, "atracker", float_format="%.4f")


# %%
def workout_layers():
    workouts = d.workouts().reset_index()
    workouts["date"] = workouts.start.dt.tz_convert(None).dt.normalize()

    workouts_pivot = pd.pivot_table(
        workouts, index="date", columns="type", values="duration", aggfunc="sum"
    )

    return write_layers(workouts_pivot, "workouts", float_format="%.4f")


# %%
def misc_layers():
    holidays = d.holidays()
    days = pd.concat(
        [
            pd.Series(1, index=pd.date_range(start, end))
            for start, end in zip(holidays.start, holidays.end)
        ]
    )
    days.index.name = "date"
    return write_layer(days, "misc", "holidays")


# %%
def git_layers():
    count = 0
    commits = d.git_commits()

    for repo, group in commits.groupby("repo"):
        layer = (
            group.assign(date=pd.to_datetime(group.datetime.dt.date))
            .groupby("date")
            .size()
        )
        count += write_layer(layer, "git", str(repo))

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
