from os import environ, path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def read_data(name: str):
    filename = path.join(environ["DIARY_DIR"], "data", f"{name}.tsv")
    df = pd.read_table(filename, parse_dates=["date"])
    df["week"] = df["date"] - pd.to_timedelta(df["date"].dt.dayofweek, unit="d")
    return df


activity = read_data("activity")
diet = read_data("diet")
weight = read_data("weight")
strength = read_data("strength")

df = pd.merge(diet, activity, how="outer").sort_values("date")


df = df[["date", "week", "calories", "activeCalories", "basalCalories"]].dropna()

df["calories"] = df["calories"].astype("int64")

df["deficit"] = df["calories"] - df["activeCalories"] - df["basalCalories"]

df.groupby("week").mean().plot(kind="bar", y="deficit")

plt.show()
