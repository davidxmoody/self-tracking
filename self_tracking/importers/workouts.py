from os.path import expandvars
from pathlib import Path
from yaspin import yaspin
import pandas as pd
import self_tracking.data as d

import_dir = Path(
    expandvars("$HOME/Library/Mobile Documents/com~apple~CloudDocs/Health/Workouts")
)

export_dir = Path(expandvars("$DIARY_DIR/data/workouts"))


def write_tsv(df: pd.DataFrame, name: str):
    output_filename = expandvars(f"$DIARY_DIR/data/workouts/{name}.tsv")
    df["duration"] = df.duration.apply(lambda dur: str(dur).replace("0 days ", ""))
    df.to_csv(output_filename, sep="\t", float_format="%.2f")


def main():
    with yaspin(text="Workouts") as spinner:
        count = 0

        import_file = sorted(import_dir.glob("*.txt"))[-1]

        df = pd.read_csv(import_file)

        df["start"] = pd.to_datetime(
            df.Date.replace(" - .*", "", regex=True)
        ).dt.tz_localize("Europe/London")
        df = df.set_index("start")

        df["duration"] = pd.to_timedelta(df["Duration(s)"].round(), unit="s")

        df["distance"] = df["Distance(mi)"]

        df["calories"] = df["Active energy burned(Cal)"].round().astype(int)

        for workout_type, group in df.groupby("Activity"):
            match workout_type:
                case "Cycling":
                    workout_df = d.cycling_outdoor()
                    size_before = workout_df.shape[0]
                    workout_df = pd.concat(
                        [workout_df, group[["duration", "distance", "calories"]]]
                    )
                    workout_df = workout_df[~workout_df.index.duplicated()].sort_index()
                    write_tsv(workout_df, "cycling-outdoor")
                    count += workout_df.shape[0] - size_before

                case _:
                    raise Exception(f"Unknown workout type: {workout_type}")

        spinner.text += f" ({count} new workouts)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
