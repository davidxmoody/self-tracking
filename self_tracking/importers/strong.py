from self_tracking.dirs import diary_dir, downloads_dir
import numpy as np
import pandas as pd
from yaspin import yaspin

fresh_path = downloads_dir / "strong_workouts.csv"
export_path = diary_dir / "data/exports/strong.csv"

workouts_path = diary_dir / "data/workouts/strength.tsv"
exercises_path = diary_dir / "data/strength-exercises.tsv"


def parse_duration(value: str):
    hours = 0.0
    for part in value.split(" "):
        if part[-1] == "h":
            hours += float(part[:-1])
        elif part[-1] == "m":
            hours += float(part[:-1]) / 60
    return f"{hours:.4f}"


def main():
    with yaspin(text="Strong") as spinner:
        if not fresh_path.exists():
            spinner.text += " (skipped)"
            spinner.ok("→")
            return

        fresh_path.rename(export_path)

        df = pd.read_csv(export_path, parse_dates=["Date"])

        df = pd.DataFrame(
            {
                "start": pd.to_datetime(df.Date).dt.tz_localize("Europe/London"),
                "duration": df.Duration.apply(parse_duration),
                "title": df["Workout Name"],
                "exercise": df["Exercise Name"],
                "weight": df.Weight.replace(0, np.nan),
                "reps": df.Reps.replace(0, np.nan).astype("Int64"),
                "seconds": df.Seconds.replace(0, np.nan).astype("Int64"),
            }
        )

        # Fix period where I thought old barbell was heavier than it actually was
        df.loc[
            (df.start >= "2020-10-30")
            & (df.start < "2022-03-11")
            & (df.exercise.str.contains("Barbell")),
            "weight",
        ] -= 2.5

        workouts_df = df[["start", "duration"]].drop_duplicates()
        workouts_df.to_csv(workouts_path, sep="\t", index=False)

        df.to_csv(exercises_path, sep="\t", index=False)

        spinner.ok("✔")


if __name__ == "__main__":
    main()
