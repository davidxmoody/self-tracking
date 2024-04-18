from datetime import timedelta
from os.path import expandvars
import re
import subprocess

import pandas as pd


event_regex = re.compile(
    r"^• (?P<category>[A-Za-z ]+)\n"
    r"    (?P<start_date>\d{4}-\d{2}-\d{2})"
    r" at (?P<start_time>\d{2}:\d{2}:\d{2})"
    r"(?P<timezone>\+\d{4})"
    r" - (?P<end_date_optional>\d{4}-\d{2}-\d{2})?(?: at )?"
    r"(?P<end_time>\d{2}:\d{2}:\d{2})"
    r"\+\d{4}$",  # Second timezone is incorrect if event spans timezone boundary
    re.MULTILINE,
)


def get_events(since: str):
    result = subprocess.run(
        [
            "icalBuddy",
            "--dateFormat",
            "%Y-%m-%d",
            "--timeFormat",
            "%H:%M:%S%z",
            "--includeEventProps",
            "title,datetime",
            "-nrd",
            "-nc",
            "-ic",
            "ATracker",
            f"eventsFrom:{since}",
            f"to:3000-12-31",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    df = pd.DataFrame(
        {
            "start": f"{m.group('start_date')} {m.group('start_time')}{m.group('timezone')}",
            "end": f"{m.group('end_date_optional') or m.group('start_date')} {m.group('end_time')}{m.group('timezone')}",
            "category": m.group("category").lower(),
        }
        for m in event_regex.finditer(result.stdout)
    )

    df["start"] = df.start.astype("datetime64[s, Europe/London]")
    df["end"] = df.end.astype("datetime64[s, Europe/London]")
    df["duration"] = (df.end - df.start).dt.total_seconds().astype(int)

    df.loc[df.category == "side project", "category"] = "project"
    df = df.loc[df.category != "cooking"]

    df = df.sort_values("start").reset_index(drop=True)

    return df[["start", "duration", "category"]]


def main():
    existing_df = pd.read_table(expandvars("$DIARY_DIR/data/atracker.tsv"))
    existing_df["start"] = existing_df.start.astype("datetime64[s, Europe/London]")

    since = existing_df.iloc[-1, 0] - timedelta(days=7)
    new_df = get_events(since)

    merged_df = (
        pd.concat([existing_df, new_df])
        .sort_values("start")
        .drop_duplicates()
        .reset_index(drop=True)
    )

    merged_df.to_csv(expandvars("$DIARY_DIR/data/atracker.tsv"), sep="\t", index=False)
    print(f"Added {merged_df.shape[0] - existing_df.shape[0]} new events")


if __name__ == "__main__":
    main()
