from io import StringIO
from os.path import expandvars
import subprocess
from yaspin import yaspin

import pandas as pd


def main():
    with yaspin(text="Climbing") as spinner:
        result = subprocess.run(
            ["shortcuts", "run", "Climbing Export"],
            check=True,
            capture_output=True,
            text=True,
        )

        df = pd.read_table(
            StringIO(result.stdout), header=None, names=["start", "end", "title"]
        )
        df["start"] = pd.to_datetime(df.start, utc=True).dt.tz_convert("Europe/London")
        df["end"] = pd.to_datetime(df.end, utc=True).dt.tz_convert("Europe/London")
        df["duration"] = ((df.end - df.start).dt.total_seconds() / 60).astype(int)
        df["date"] = df.start.dt.date
        df["place"] = df.title.str.replace("Climbing at ", "")
        df = df[["date", "duration", "place"]]

        df.to_csv(expandvars("$DIARY_DIR/data/climbing.tsv"), sep="\t", index=False)

        spinner.ok("✔")


if __name__ == "__main__":
    main()
