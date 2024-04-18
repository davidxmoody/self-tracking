from datetime import timedelta
from math import ceil

import matplotlib.pyplot as plt
import seaborn as sns

import self_tracking.data as d


# %%
df = d.strength()

workout_dates = df.date.unique()
programs = d.strength_programs()
programs["num"] = programs.apply(
    lambda row: sum(1 for w in workout_dates if w >= row.start and w <= row.end), axis=1
)

tracked_exercises = {
    "Deadlift (Barbell)": "Deadlift",
    "Squat (Barbell)": "Squat",
    "Bench Press (Barbell)": "Bench",
    "Overhead Press (Barbell)": "Overhead",
}

df = df.loc[
    df.exercise.isin(tracked_exercises),
    ["date", "exercise", "weight", "reps"],
]

df["exercise"] = df.exercise.map(tracked_exercises)

df["onerepmax"] = df.weight / (1.0278 - 0.0278 * df.reps)


# %%
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
            ("2021-03-08", "Squat"),
            ("2021-03-09", "Bench"),
            ("2021-03-11", "Squat"),
            ("2021-04-01", "Squat"),
            ("2021-04-08", "Squat"),
            ("2021-04-17", "Squat"),
            ("2021-06-04", "Squat"),
            ("2022-04-08", "Overhead"),
            ("2023-05-09", "Bench"),
            ("2023-05-09", "Deadlift"),
            ("2023-05-10", "Squat"),
        ]
    )
    .reset_index()
)


# %%
sns.lineplot(
    dfl,
    x="date",
    y="onerepmax",
    hue="exercise",
    hue_order=tracked_exercises.values(),
    marker="o",
)

top_edge = ceil(dfl.onerepmax.max() / 20) * 20 + 20
left_edge = programs.iloc[0].start
right_edge = dfl.iloc[-1].date + timedelta(days=90)

plt.ylim(bottom=0, top=top_edge)
plt.xlim(left=left_edge, right=right_edge)

for i, (start, end, duration, name, num) in enumerate(programs.values):
    xmiddle = start + ((right_edge if i == len(programs) - 1 else end) - start) / 2
    months = round(duration.days / 30)

    plt.text(
        x=xmiddle,
        y=top_edge - 10,
        s=name,
        horizontalalignment="center",
        verticalalignment="bottom",
        weight="bold",
        fontsize=12,
    )
    plt.text(
        x=xmiddle,
        y=top_edge - 11,
        s=f"{num} workout{'' if num == 1 else 's'}\n{months} month{'' if months == 1 else 's'}",
        horizontalalignment="center",
        verticalalignment="top",
        fontsize=6,
    )

plt.title("Strength training history", fontsize=20, weight="bold", pad=25)

plt.xlabel("Date", weight="bold")
plt.ylabel("One rep max (kg)", labelpad=15, weight="bold")

plt.legend(loc="lower right")

plt.xticks(programs.start, rotation=30)

plt.subplots_adjust(bottom=0.15)

plt.gca().xaxis.grid(True, linestyle="--", linewidth=1, color="black", alpha=0.4)
plt.gca().yaxis.grid(True, linestyle="-", linewidth=1, color="black", alpha=0.1)

plt.show()
