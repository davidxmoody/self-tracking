from self_tracking.dirs import diary_dir, icloud_dir
from yaspin import yaspin
import pandas as pd

import_dir = icloud_dir / "Health/Workouts"
export_dir = diary_dir / "data/workouts"


def main():
    with yaspin(text="Workouts") as spinner:
        count = 0

        import_file = sorted(import_dir.glob("*.txt"))[-1]

        df = pd.read_csv(import_file)

        df["start"] = (
            pd.to_datetime(df.Date.replace(" - .*", "", regex=True))
            .dt.tz_localize("Europe/London")
            .astype(str)
        )

        df["duration"] = df["Duration(s)"] / (60 * 60)

        df["distance"] = df["Distance(mi)"] if "Distance(mi)" in df else 0

        df["calories"] = df["Active energy burned(Cal)"].round().astype("Int64")

        for workout_type, group in df.groupby("Activity"):
            match workout_type:
                case "Cycling":
                    filepath = export_dir / "cycling.tsv"

                    workout_df = pd.read_table(filepath)
                    size_before = workout_df.shape[0]

                    workout_df = pd.concat(
                        [
                            workout_df,
                            group[["start", "duration", "distance", "calories"]],
                        ]
                    )
                    workout_df["duration"] = workout_df.duration.apply(
                        lambda x: f"{x:.4f}"
                    )
                    workout_df["distance"] = workout_df.distance.apply(
                        lambda x: f"{x:.2f}"
                    )
                    workout_df = workout_df.drop_duplicates("start")

                    count += workout_df.shape[0] - size_before
                    workout_df.to_csv(filepath, sep="\t", index=False)

                case "Traditional Strength Training (Indoor)":
                    filepath = export_dir / "strength.tsv"

                    workout_df = pd.read_table(filepath)
                    size_before = workout_df.shape[0]

                    workout_df = pd.concat([workout_df, group[["start", "duration"]]])
                    workout_df["duration"] = workout_df.duration.apply(
                        lambda x: f"{x:.4f}"
                    )
                    workout_df = workout_df.drop_duplicates("start")

                    count += workout_df.shape[0] - size_before
                    workout_df.to_csv(filepath, sep="\t", index=False)

                case "Walking":
                    pass

                case _:
                    raise Exception(f"Unknown workout type: {workout_type}")

        spinner.text += f" ({count} workouts)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
