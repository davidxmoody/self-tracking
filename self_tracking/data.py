from datetime import datetime, timedelta
from os.path import expandvars
from typing import Any, cast

import pandas as pd


# %%
def filepath(name: str):
    return expandvars(f"$DIARY_DIR/data/{name}.tsv")


def read_date_indexed(name: str):
    df = pd.read_table(filepath(name), parse_dates=["date"], index_col="date")
    if "duration" in df.columns:
        df["duration"] = pd.to_timedelta(df.duration)
    return df


def read_events(name: str, index_col: str | None = "start"):
    df = pd.read_table(filepath(name))
    df["start"] = pd.to_datetime(df.start, utc=True).dt.tz_convert("Europe/London")
    df["duration"] = pd.to_timedelta(df.duration)
    if index_col:
        df = df.set_index(index_col)
    return df


# %%
def atracker_events():
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
    return df


def atracker_categories() -> dict[str, str]:
    df = pd.read_table(filepath("atracker-categories"), index_col="category")
    return df.color.to_dict()


def atracker():
    df = atracker_events().pivot_table(
        values="duration", index="date", columns="category", aggfunc="sum"
    )
    return df.fillna(df.mask(df.ffill().notna(), pd.to_timedelta(0)))


def atracker_heatmap(start_date="2020"):
    categories = list(atracker_categories())
    minutes_in_day = 24 * 60
    heatmap = pd.DataFrame(0, index=range(minutes_in_day), columns=categories)

    events = atracker_events()
    events = events.loc[events.date > start_date]

    for event in events.itertuples(index=False):
        event: Any = event
        start_minute = event.start.hour * 60 + event.start.minute
        num_minutes = round(event.duration.total_seconds() / 60)
        for minute in range(start_minute, start_minute + num_minutes):
            heatmap.loc[minute % minutes_in_day, event.category] += cast(Any, 1)

    return heatmap


# %%
def climbing():
    return read_events("workouts/climbing")


def cycling_indoor():
    return read_events("workouts/cycling-indoor")


def cycling_outdoor():
    # TODO rename this to just "cycling"
    return read_events("workouts/cycling-outdoor")


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
        cycling_outdoor().assign(type="cycling"),
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
    for column in df:
        df[column] = df[column].apply(lambda x: pd.to_timedelta(x, unit="s"))
    return df


def weight():
    return read_date_indexed("weight")


def net_calories():
    eaten = diet().calories
    activity_df = activity()
    active = activity_df.active_calories
    basal = activity_df.basal_calories
    return (eaten - active - basal).dropna().astype(int)


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
