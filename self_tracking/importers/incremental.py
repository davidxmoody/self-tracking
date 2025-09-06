from self_tracking.dirs import diary_dir, icloud_dir
from pathlib import Path
from yaspin import yaspin
import pandas as pd


def get_latest_and_cleanup(dir: Path, pattern: str = "*.txt"):
    files = sorted(dir.glob(pattern))
    if not files:
        return None
    for file in files[:-1]:
        file.unlink()
    return files[-1]


def activity():
    import_file = get_latest_and_cleanup(icloud_dir / "Health/ActiveEnergy")
    if not import_file:
        return 0

    df = pd.read_csv(import_file)
    df = df.rename(
        columns={"Date": "date", "Active energy burned(Cal)": "active_calories"}
    )
    df = df.iloc[:-1]
    df["active_calories"] = df.active_calories.round(0).astype(int)

    data_file = diary_dir / "data/activity.tsv"
    existing_df = pd.read_table(data_file)
    old_size = existing_df.shape[0]

    new_df = pd.concat([existing_df, df.loc[~df.date.isin(existing_df.date)]])
    new_df.to_csv(data_file, index=False, sep="\t")

    return new_df.shape[0] - old_size


def eaten():
    import_file = get_latest_and_cleanup(icloud_dir / "Health/EatenEnergy")
    if not import_file:
        return 0

    df = pd.read_csv(import_file)
    df = df.rename(columns={"Date": "date", "Energy consumed(Cal)": "calories"})
    df = df.iloc[:-1]
    df["calories"] = df.calories.round(0).astype(int)

    data_file = diary_dir / "data/diet.tsv"
    existing_df = pd.read_table(data_file, dtype=str)
    old_size = existing_df.shape[0]

    new_df = pd.concat([existing_df, df.loc[~df.date.isin(existing_df.date)]])
    new_df.to_csv(data_file, index=False, sep="\t")

    return new_df.shape[0] - old_size


def weight():
    import_file = get_latest_and_cleanup(icloud_dir / "Health/Weight")
    fat_import_file = get_latest_and_cleanup(icloud_dir / "Health/Fat")
    if not import_file or not fat_import_file:
        return 0

    df = pd.read_csv(import_file, parse_dates=["Date"])
    df = df.rename(columns={"Date": "date", "Body mass(lb)": "weight"})

    if df.shape[0] == 0:
        return 0

    df["date"] = df.date.dt.date.astype(str)
    df = df.groupby("date").min()
    df["weight"] = df.weight.apply(lambda x: f"{x:.2f}")

    fat_df = pd.read_csv(fat_import_file, parse_dates=["Date"])
    fat_df = fat_df.rename(columns={"Date": "date", "Body fat percentage(%)": "fat"})
    fat_df["date"] = fat_df.date.dt.date.astype(str)
    fat_df = fat_df.groupby("date").min()
    df["fat"] = fat_df.fat.apply(lambda x: f"{x:.3f}")

    df = df.reset_index()

    data_file = diary_dir / "data/weight.tsv"
    existing_df = pd.read_table(data_file, dtype=str)
    old_size = existing_df.shape[0]

    new_df = pd.concat([existing_df, df.loc[~df.date.isin(existing_df.date)]])
    new_df.to_csv(data_file, index=False, sep="\t")

    return new_df.shape[0] - old_size


def main():
    with yaspin(text="Apple Health incremental") as spinner:
        count = 0
        count += activity()
        count += eaten()
        count += weight()

        spinner.text += f" ({count} records)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
