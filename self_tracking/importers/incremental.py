from os.path import expandvars
from pathlib import Path
from yaspin import yaspin
import pandas as pd

health_dir = Path("~/Library/Mobile Documents/com~apple~CloudDocs/Health").expanduser()
data_dir = Path(expandvars("$DIARY_DIR/data"))


def get_latest_and_cleanup(dir: Path, pattern: str = "*.txt"):
    files = sorted(dir.glob(pattern))
    if not files:
        return None
    for file in files[:-1]:
        file.unlink()
    return files[-1]


def activity():
    import_file = get_latest_and_cleanup(health_dir / "ActiveEnergy")
    if not import_file:
        return 0

    df = pd.read_csv(import_file)
    df = df.rename(
        columns={"Date": "date", "Active energy burned(Cal)": "active_calories"}
    )
    df = df.iloc[:-1]
    df["active_calories"] = df.active_calories.round(0).astype(int)

    data_file = data_dir / "activity.tsv"
    existing_df = pd.read_table(data_file)
    old_size = existing_df.shape[0]

    new_df = pd.concat([existing_df, df.loc[~df.date.isin(existing_df.date)]])
    new_df.to_csv(data_file, index=False, sep="\t")

    return new_df.shape[0] - old_size


def eaten():
    import_file = get_latest_and_cleanup(health_dir / "EatenEnergy")
    if not import_file:
        return 0

    df = pd.read_csv(import_file)
    df = df.rename(columns={"Date": "date", "Energy consumed(Cal)": "calories"})
    df = df.iloc[:-1]
    df["calories"] = df.calories.round(0).astype(int)

    data_file = data_dir / "diet.tsv"
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

        spinner.text += f" ({count} records)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
