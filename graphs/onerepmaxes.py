# %% Imports

from os.path import expandvars

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


# %% Load data

df = pd.read_table(expandvars("$DIARY_DIR/data/strength.tsv"), parse_dates=["date"])

tracked_exercises = {
    "Deadlift (Barbell)": "deadlift",
    "Squat (Barbell)": "squat",
    "Bench Press (Barbell)": "bench",
    "Overhead Press (Barbell)": "overhead",
}

df = df.loc[
    df.exercise.isin(tracked_exercises),
    ["date", "exercise", "weight", "reps"],
]

df["exercise"] = df.exercise.map(tracked_exercises)

df["onerepmax"] = df.weight / (1.0278 - 0.0278 * df.reps)


# %% Format data

# Exclude days where the exercise was done for high volume (and ignore warmups)
dfl = (
    df.sort_values(["date", "exercise", "onerepmax"])
    .drop_duplicates(subset=["date", "exercise"], keep="last")
    .query("reps < 10")
)

# Exclude one-offs that make the graph look bad
dfl = (
    dfl.set_index(["date", "exercise"])
    .drop(
        [
            ("2021-03-08", "squat"),
            ("2021-03-09", "bench"),
            ("2021-03-11", "squat"),
            ("2021-04-01", "squat"),
            ("2021-04-08", "squat"),
            ("2021-04-17", "squat"),
            ("2021-06-04", "squat"),
            ("2022-04-08", "overhead"),
            ("2023-05-09", "bench"),
            ("2023-05-09", "deadlift"),
            ("2023-05-10", "squat"),
        ]
    )
    .reset_index()
)


# %% Graph

plt.ion()
plt.clf()

sns.lineplot(dfl, x="date", y="onerepmax", hue="exercise", marker="o")

plt.show()
