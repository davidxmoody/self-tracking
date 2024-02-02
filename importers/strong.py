# %% Imports

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


# %% Load data

df = pd.read_csv(expandvars("$HOME/Downloads/strong.csv"))

df = pd.DataFrame(
    {
        "datetime": pd.to_datetime(df.Date),
        "workout_name": df["Workout Name"],
        "duration_minutes": df.Duration.apply(parse_duration),
        "exercise_name": df["Exercise Name"],
        "set_order": df["Set Order"],
        "weight": df.Weight.replace(0, np.nan),
        "reps": df.Reps.replace(0, np.nan),
        "seconds": df.Seconds.replace(0, np.nan),
    }
)

# Fix period where I thought old barbell was heavier than it actually was
df.loc[
    (df.datetime >= "2020-10-30")
    & (df.datetime < "2022-03-11")
    & (df.exercise_name.str.contains("Barbell")),
    "weight",
] -= 2.5


# %% Write data

df.to_csv(expandvars("$DIARY_DIR/data/strength.tsv"), sep="\t", index=False)
