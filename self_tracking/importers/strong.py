from pathlib import Path
from os.path import expandvars
import numpy as np
import pandas as pd
from yaspin import yaspin

input_path = Path("~/Downloads/strong.csv").expanduser()
output_path = Path(expandvars("$DIARY_DIR/data/workouts/strength.tsv"))


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
        if not input_path.exists():
            spinner.text += " (skipped)"
            spinner.ok("→")
            return

        df = pd.read_csv(input_path, parse_dates=["Date"])

        df = pd.DataFrame(
            {
                "start": pd.to_datetime(df.Date).dt.tz_localize("Europe/London"),
                "duration": df.Duration.apply(parse_duration),
                "title": df["Workout Name"],
                "exercise": df["Exercise Name"],
                "weight": df.Weight.replace(0, np.nan),
                "reps": df.Reps.replace(0, np.nan),
                "seconds": df.Seconds.replace(0, np.nan),
            }
        )

        # Fix period where I thought old barbell was heavier than it actually was
        df.loc[
            (df.start >= "2020-10-30")
            & (df.start < "2022-03-11")
            & (df.exercise.str.contains("Barbell")),
            "weight",
        ] -= 2.5

        df.to_csv(output_path, sep="\t", index=False)

        spinner.ok("✔")


if __name__ == "__main__":
    main()
