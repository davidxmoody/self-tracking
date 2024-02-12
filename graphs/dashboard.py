# %% Imports

from datetime import datetime, timedelta
from os.path import expandvars

import numpy as np
import pandas as pd


# %% Load


def read_data(name: str, index_col: str | None = "date"):
    return pd.read_table(
        expandvars(f"$DIARY_DIR/data/{name}.tsv"),
        parse_dates=["date"],
        index_col=index_col,
    )


strength = read_data("strength", index_col=None)
running = read_data("running")
climbing = read_data("climbing")


atracker_events = pd.read_table(expandvars("$DIARY_DIR/data/atracker.tsv"))
atracker_events["start"] = atracker_events.start.astype("datetime64[s, Europe/London]")
atracker_events["date"] = pd.to_datetime(
    (atracker_events.start - timedelta(hours=4)).dt.date
)
atracker_events = atracker_events.query("date >= '2020'")

atracker = atracker_events.pivot_table(
    values="duration", index="date", columns="category", aggfunc="sum"
)
atracker = atracker.fillna(atracker.mask(atracker.ffill().notna(), 0))


# %% Graph


def color_block(rgb: tuple[int, int, int], intensity: float):
    (r, g, b) = (round(x * intensity) for x in rgb)
    text_code = f"38;2;255;255;255"
    background_code = f"48;2;{r};{g};{b}"
    return f"\033[{text_code};{background_code}m  \033[0m"


def colorize(rgb: tuple[int, int, int], value: float):
    if np.isnan(value) or value == 0:
        return color_block((50, 50, 50), 1)
    return color_block(rgb, value)


num_weeks = 70
today = datetime.today().date()
start = today - timedelta(days=today.weekday() + 7 * (num_weeks - 1))
drange = pd.date_range(start, today, freq="D")

data = [
    (
        "Strength",
        (255, 50, 50),
        strength.drop_duplicates("date")
        .set_index("date")
        .title.reindex(drange)
        .notna(),
    ),
    (
        "Running",
        (50, 255, 50),
        (running.reindex(drange).distance / 5).clip(0, 1),
    ),
    (
        "Climbing",
        (50, 50, 255),
        (climbing.reindex(drange).duration / 120).clip(0, 1),
    ),
    (
        "Project",
        (10, 200, 10),
        (atracker.reindex(drange).project / (4 * 60 * 60)).clip(0, 1),
    ),
    (
        "Social",
        (10, 10, 200),
        (atracker.reindex(drange).social / (6 * 60 * 60)).clip(0, 1),
    ),
]

for i in range(num_weeks):
    line = f"{data[0][2].index[i * 7].date()}:"
    for _, dc, d in data:
        row = [colorize(dc, x) for x in d[i * 7 : (i + 1) * 7]]
        line += "    " + "".join(row) + ("  " * (7 - len(row)))
    print(line)

print()
title_line = "               "
for name, _, _ in data:
    title_line += name.ljust(14, " ") + "    "
print(title_line)
