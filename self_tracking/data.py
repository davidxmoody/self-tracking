from datetime import datetime, timedelta
from os.path import expandvars, getmtime
from typing import Any, cast
import pandas as pd


# %%
def filepath(name: str):
    return expandvars(f"$DIARY_DIR/data/{name}.tsv")


def read_date_indexed(name: str):
    return pd.read_table(filepath(name), parse_dates=["date"], index_col="date")


def read_events(name: str, index_col: str | None = "start"):
    df = pd.read_table(filepath(name))
    df["start"] = pd.to_datetime(df.start, utc=True).dt.tz_convert("Europe/London")
    if index_col:
        df = df.set_index(index_col)
    return df


# %%
def atracker_events(start_date: str | None = None):
    df = (
        pd.concat(
            [
                workouts()[["duration"]].reset_index().assign(category="workout"),
                read_events("meditation", index_col=None).assign(category="meditation"),
                read_events("atracker", index_col=None).query("category != 'workout'"),
            ]
        )
        .sort_values("start")
        .reset_index(drop=True)
    )

    df["date"] = pd.to_datetime((cast(Any, df.start) - pd.Timedelta(hours=4)).dt.date)

    if start_date:
        df = df.loc[df.date >= start_date]

    return df


def atracker_mtime():
    names = [
        "atracker",
        "meditation",
        "workouts/climbing",
        "workouts/cycling-indoor",
        "workouts/cycling",
        "workouts/running",
        "workouts/strength",
    ]
    return max(getmtime(filepath(name)) for name in names)


def atracker_categories():
    return pd.read_table(filepath("atracker-categories"), index_col="category")


def atracker_color_map(use_names=False) -> dict[str, str]:
    categories = atracker_categories()
    if use_names:
        categories = categories.set_index("name")
    return categories.color.to_dict()


def atracker(start_date: str | None = "2020-05-04", use_names=False):
    df = atracker_events(start_date).pivot_table(
        values="duration", index="date", columns="category", aggfunc="sum"
    )

    full_range = pd.date_range(
        start=df.index.min(), end=df.index.max(), freq="D"
    ).rename("date")

    df = df.reindex(full_range, fill_value=0.0).fillna(0.0)

    if use_names:
        names = atracker_categories().name
        df.columns = df.columns.map(names)

    return df


def atracker_heatmap(start_date="2020-05-04"):
    categories = list(atracker_categories().index)
    minutes_in_day = 24 * 60
    heatmap = pd.DataFrame(0, index=range(minutes_in_day), columns=categories)

    events = atracker_events(start_date)

    for event in events.itertuples(index=False):
        event: Any = event
        start_minute = event.start.hour * 60 + event.start.minute
        num_minutes = round(event.duration * 60)
        for minute in range(start_minute, start_minute + num_minutes):
            heatmap.loc[minute % minutes_in_day, event.category] += cast(Any, 1)

    return heatmap


# %%
def climbing():
    return read_events("workouts/climbing")


def cycling_indoor():
    return read_events("workouts/cycling-indoor")


def cycling():
    return read_events("workouts/cycling")


def running():
    return read_events("workouts/running")


def strength():
    df = read_events("workouts/strength", index_col=None)
    df["reps"] = df.reps.astype("Int64")
    return df


def strength_programs():
    df = pd.read_table(filepath("strength-programs"), parse_dates=["start"])
    df["end"] = df.start.shift(-1) - pd.to_timedelta(1, unit="D")
    df["end"] = df.end.fillna(pd.to_datetime(datetime.now().date()))
    df["duration"] = df.end - df.start + pd.to_timedelta(1, unit="D")
    return df[["start", "end", "duration", "name"]]


def workouts():
    events = [
        climbing().assign(type="climbing"),
        cycling_indoor().assign(type="cycling_indoor"),
        cycling().assign(type="cycling"),
        running().assign(type="running"),
        strength().drop_duplicates("start").set_index("start").assign(type="strength"),
    ]

    return pd.concat([df[["duration", "type"]] for df in events]).sort_index()


# %%
def activity():
    return read_date_indexed("activity")


def diet():
    return read_date_indexed("diet")


def sleep():
    df = read_date_indexed("sleep")
    df["Asleep"] = df.Deep + df.Core + df.REM
    return df


def weight():
    return read_date_indexed("weight")


# %%
def eras():
    df = pd.read_table(filepath("eras"), parse_dates=["start"])
    df["end"] = df.start.shift(-1) - pd.to_timedelta(1, unit="D")
    df["end"] = df.end.fillna(pd.to_datetime(datetime.now().date()))
    df["duration"] = df.end - df.start + pd.to_timedelta(1, unit="D")
    return df[["start", "end", "duration", "name", "color"]]


def holidays():
    df = pd.read_table(filepath("holidays"), parse_dates=["start", "end"])
    df["duration"] = df.end - df.start + timedelta(days=1)
    return df[["start", "end", "duration", "name"]]


def streaks():
    return pd.read_table(filepath("streaks"), parse_dates=["date"])
