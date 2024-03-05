# %% Imports

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import self_tracking.data as d


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
        d.strength()
        .drop_duplicates("date")
        .set_index("date")
        .title.reindex(drange)
        .notna(),
    ),
    (
        "Running",
        (50, 255, 50),
        (d.running().reindex(drange).distance / 5).clip(0, 1),
    ),
    (
        "Climbing",
        (50, 50, 255),
        (d.climbing().reindex(drange).duration.dt.total_seconds() / (2 * 60 * 60)).clip(
            0, 1
        ),
    ),
    (
        "Project",
        (10, 200, 10),
        (d.atracker().reindex(drange).project.dt.total_seconds() / (4 * 60 * 60)).clip(
            0, 1
        ),
    ),
    (
        "Social",
        (10, 10, 200),
        (d.atracker().reindex(drange).social.dt.total_seconds() / (6 * 60 * 60)).clip(
            0, 1
        ),
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
