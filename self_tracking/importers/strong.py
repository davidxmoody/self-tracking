# %% Imports

from datetime import date
from os.path import expandvars

import numpy as np
import pandas as pd


# %% Helpers


def parse_duration(value: str):
    minutes = 0
    for part in value.split(" "):
        if part[-1] == "h":
            minutes += 60 * int(part[:-1])
        elif part[-1] == "m":
            minutes += int(part[:-1])
    return minutes


# %% Load

df = pd.read_csv(expandvars("$HOME/Downloads/strong.csv"), parse_dates=["Date"])

df = pd.DataFrame(
    {
        "date": df.Date.dt.date,
        "time": df.Date.dt.time,
        "title": df["Workout Name"],
        "duration": df.Duration.apply(parse_duration),
        "exercise": df["Exercise Name"],
        "weight": df.Weight.replace(0, np.nan),
        "reps": df.Reps.replace(0, np.nan),
        "seconds": df.Seconds.replace(0, np.nan),
    }
)

# Fix period where I thought old barbell was heavier than it actually was
df.loc[
    (df.date >= date(2020, 10, 30))
    & (df.date < date(2022, 3, 11))
    & (df.exercise.str.contains("Barbell")),
    "weight",
] -= 2.5


# %% Write

df.to_csv(expandvars("$DIARY_DIR/data/strength.tsv"), sep="\t", index=False)
