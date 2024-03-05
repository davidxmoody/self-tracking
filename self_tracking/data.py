# %% Imports

from datetime import timedelta
from os.path import expandvars

import pandas as pd


# %% Helpers


def filepath(name: str):
    return expandvars(f"$DIARY_DIR/data/{name}.tsv")


def read_data(name: str, parse_dates=["date"], index_col: str | None = "date"):
    return pd.read_table(
        filepath(name),
        parse_dates=parse_dates,
        index_col=index_col,
    )


# %% Data


def activity():
    return read_data("activity")


def atracker_events():
    df = pd.read_table(filepath("atracker"))
    df["start"] = df.start.astype("datetime64[s, Europe/London]")
    df["date"] = pd.to_datetime((df.start - timedelta(hours=4)).dt.date)
    df["duration"] = pd.to_timedelta(df.duration, unit="s")
    return df


def climbing():
    return read_data("climbing")


def cycling_indoor():
    return read_data("cycling-indoor")


def cycling_outdoor():
    return read_data("cycling-outdoor")


def diet():
    return read_data("diet")


def eras():
    # TODO maybe add on end and duration (in days)?
    return read_data("eras", parse_dates=["start"], index_col=None)


def holidays():
    df = read_data("holidays", parse_dates=["start", "end"], index_col=None)
    df["duration"] = df.end - df.start + timedelta(days=1)
    return df


def meditation():
    return read_data("meditation")


def running():
    return read_data("running")


def sleep():
    # TODO maybe parse durations?
    return read_data("sleep")


def social():
    # TODO this is old data and date index maybe won't work for everything
    return read_data("social")


def streaks():
    return read_data("streaks", index_col=None)


def strength():
    # TODO rename to strength_sets
    return read_data("strength", index_col=None)


def weight():
    return read_data("weight")


# %% Derived data


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
