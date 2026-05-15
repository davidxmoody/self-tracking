import json
import re

from self_tracking.dirs import diary_dir

import pandas as pd
from yaspin import yaspin

import self_tracking.data as d


# %%
def write_layer(
    series,
    group: str,
    name: str,
    *,
    title: str,
    group_title: str,
    color: str,
    order: int,
    ndigits: int,
) -> int:
    file = diary_dir / "layers" / group / f"{name}.json"
    file.parent.mkdir(parents=True, exist_ok=True)
    old_contents = file.read_text() if file.exists() else None

    series = series[series > 0]
    data = {
        k.strftime("%Y-%m-%d"): int(v) if ndigits == 0 else round(float(v), ndigits)
        for k, v in series.items()
    }

    payload = {
        "id": f"{group}/{name}",
        "title": title,
        "groupTitle": group_title,
        "color": color,
        "order": order,
        "data": data,
    }
    new_contents = json.dumps(payload, indent=2) + "\n"

    has_changed = old_contents != new_contents

    if has_changed:
        file.write_text(new_contents)

    return int(has_changed)


# %%
def streaks_layers():
    streaks = d.streaks()
    streaks["score"] = streaks.value.map({"completed": 1, "skipped": 0.3, "missed": 0})

    pivot = streaks.pivot_table(values="score", index="date", columns="name")

    count = 0
    for order, name in enumerate(pivot.columns):
        count += write_layer(
            pivot[name],
            "streaks",
            str(name),
            title=str(name).title(),
            group_title="Streaks",
            color="#FF704D",
            order=order,
            ndigits=1,
        )
    return count


# %%
def atracker_layers():
    categories = d.atracker_categories()
    atracker = d.atracker(start_date=None)

    count = 0
    for order, cat in enumerate(categories.index):
        if cat not in atracker.columns:
            continue
        count += write_layer(
            atracker[cat],
            "atracker",
            str(cat),
            title=str(categories.loc[cat, "name"]),
            group_title="ATracker",
            color=str(categories.loc[cat, "color"]),
            order=order,
            ndigits=4,
        )
    return count


# %%
def workout_layers():
    workouts = d.workouts().reset_index()
    workouts["date"] = workouts.start.dt.tz_convert(None).dt.normalize()

    pivot = pd.pivot_table(
        workouts, index="date", columns="type", values="duration", aggfunc="sum"
    )

    count = 0
    for order, name in enumerate(pivot.columns):
        count += write_layer(
            pivot[name],
            "workouts",
            str(name),
            title=str(name),
            group_title="Workouts",
            color="#3AA8BC",
            order=order,
            ndigits=4,
        )
    return count


# %%
def health_layers():
    weight = d.weight()["weight"]
    weight = weight.reindex(pd.date_range(weight.index.min(), weight.index.max()))
    weight = weight.interpolate(method="linear")
    rate = weight.diff().rolling(window=29, center=True, min_periods=1).mean()
    rate = rate.rank(pct=True)
    return write_layer(
        rate,
        "health",
        "weight",
        title="Weight",
        group_title="Health",
        color="#D19A66",
        order=0,
        ndigits=3,
    )


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
    return write_layer(
        days,
        "misc",
        "holidays",
        title="Holidays",
        group_title="Misc",
        color="#132748",
        order=0,
        ndigits=0,
    )


# %%
def git_layers():
    commits = d.git_commits()
    repo_counts = commits.groupby("repo").size().sort_values(ascending=False)
    order_map = {repo: i for i, repo in enumerate(repo_counts.index)}

    count = 0
    for repo, group in commits.groupby("repo"):
        layer = (
            group.assign(date=pd.to_datetime(group.datetime.dt.date))
            .groupby("date")
            .size()
        )
        count += write_layer(
            layer,
            "git",
            str(repo),
            title=str(repo),
            group_title="Git",
            color="#A6E3A1",
            order=order_map[repo],
            ndigits=0,
        )

    return count


SCANNED_RE = re.compile(r"!\[\]\(scanned-\d+\.\w+\)")
AUDIO_RE = re.compile(r"!\[\]\(audio-\d+-\d+\.\w+\)")


# %%
def diary_layers():
    wordcounts = {}
    scanned = {}
    audio = {}
    for file in (diary_dir / "entries").glob("*/*/*/diary.md"):
        year, month, day = file.parts[-4:-1]
        date = pd.Timestamp(f"{year}-{month}-{day}")
        text = file.read_text()
        wordcounts[date] = len(text.split())
        scanned[date] = len(SCANNED_RE.findall(text))
        audio[date] = len(AUDIO_RE.findall(text))

    def to_series(d):
        s = pd.Series(d).sort_index()
        s.index.name = "date"
        return s

    count = 0
    count += write_layer(
        to_series(wordcounts),
        "diary",
        "wordcount",
        title="Word count",
        group_title="Diary",
        color="#E5C07B",
        order=0,
        ndigits=0,
    )
    count += write_layer(
        to_series(scanned),
        "diary",
        "scanned",
        title="Scanned",
        group_title="Diary",
        color="#C678DD",
        order=1,
        ndigits=0,
    )
    count += write_layer(
        to_series(audio),
        "diary",
        "audio",
        title="Audio",
        group_title="Diary",
        color="#56B6C2",
        order=2,
        ndigits=0,
    )
    return count


# %%
def main():
    with yaspin(text="Layers") as spinner:
        count = 0
        count += streaks_layers()
        count += atracker_layers()
        count += workout_layers()
        count += health_layers()
        count += misc_layers()
        count += git_layers()
        count += diary_layers()
        spinner.text += f" ({count} layers)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
