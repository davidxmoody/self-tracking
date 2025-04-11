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


def read_events(name: str):
    df = pd.read_table(filepath(name))
    df["start"] = pd.to_datetime(df.start, utc=True).dt.tz_convert("Europe/London")
    df["duration"] = pd.to_timedelta(df.duration)
    return df


def read_data(name: str, parse_dates=["date"], index_col: str | None = "date"):
    return pd.read_table(
        filepath(name),
        parse_dates=parse_dates,
        index_col=index_col,
    )


# %%
def activity():
    return read_date_indexed("activity")


def atracker_events():
    df = read_events("atracker")
    df["date"] = pd.to_datetime((cast(Any, df.start) - timedelta(hours=4)).dt.date)
    return df


def atracker_categories() -> dict[str, str]:
    df = pd.read_table(filepath("atracker-categories"), index_col="category")
    return df.color.to_dict()


def climbing_events():
    return read_events("climbing")


def climbing():
    df = climbing_events()
    df["date"] = pd.to_datetime(df.start.dt.date)
    df = df[["date", "duration"]]
    df = df.groupby("date").sum()
    return df


def cycling_indoor():
    df = read_data("cycling-indoor")
    df["duration"] = pd.to_timedelta(round(df.duration * 60), unit="s")
    return df


def cycling_outdoor():
    df = read_data("cycling-outdoor")
    df["duration"] = pd.to_timedelta(round(df.duration * 60), unit="s")
    return df


def diet():
    return read_date_indexed("diet")


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


def meditation_events():
    # TODO change mindfulness name to meditation
    mdf = read_events("meditation")
    adf = atracker_events().query("category == 'mindfulness'")[["start", "duration"]]
    return pd.concat([mdf, adf])


def meditation():
    df = meditation_events()
    df["date"] = pd.to_datetime(df.start.dt.date)
    return df[["date", "duration"]].groupby("date").sum()


def running():
    df = read_data("running")
    df["calories"] = df.calories.astype("Int64")
    df["duration"] = pd.to_timedelta(
        (df.duration * 60).round().astype("Int64"), unit="s"
    )
    return df


def sleep():
    df = read_date_indexed("sleep")
    for column in df:
        df[column] = df[column].apply(lambda x: pd.to_timedelta(x, unit="s"))
    return df


def streaks():
    return pd.read_table(filepath("streaks"), parse_dates=["date"])


def strength():
    # TODO
    df = read_data("strength", index_col=None)
    df["duration"] = pd.to_timedelta(df.duration, unit="m")
    df["time"] = pd.to_datetime(df.time, format="%H:%M:%S").dt.time
    df["reps"] = df.reps.astype("Int64")
    return df


def strength_programs():
    df = read_data("strength-programs", parse_dates=["start"], index_col=None)
    df["end"] = df.start.shift(-1) - pd.to_timedelta(1, unit="D")
    df["end"] = df.end.fillna(pd.to_datetime(datetime.now().date()))
    df["duration"] = df.end - df.start + pd.to_timedelta(1, unit="D")
    return df[["start", "end", "duration", "name"]]


def weight():
    return read_date_indexed("weight")


def workouts():
    cdf = climbing_events()
    cdf["type"] = "climbing"
    cdf = cdf[["start", "type", "duration"]]

    wdf = read_data("workouts", parse_dates=None, index_col=None)
    wdf["start"] = pd.to_datetime(wdf.start, utc=True).dt.tz_convert("Europe/London")
    wdf["duration"] = pd.to_timedelta(wdf.duration, unit="m").dt.round("1s")

    return pd.concat([cdf, wdf]).sort_values("start")


def net_calories():
    eaten = diet().calories
    activity_df = activity()
    active = activity_df.active_calories
    basal = activity_df.basal_calories
    return (eaten - active - basal).dropna().astype(int)


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
