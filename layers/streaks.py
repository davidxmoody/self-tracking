# %% Imports

from datetime import timedelta
from os.path import expandvars

import pandas as pd


# %% Process


def score_week(values):
    if "completed" not in values.values:
        return 0
    score = max(0, values.map({"completed": 1, "skipped": 0.9, "missed": -2}).mean())
    return round(score * 0.8 + 0.2, 2)


df = pd.read_table(expandvars("$DIARY_DIR/data/streaks.tsv"), parse_dates=["date"])

for name in df.name.unique():
    values = df.query("name == @name").set_index("date").value
    weekly = values.resample("W").agg(score_week)
    weekly.index = (weekly.index - timedelta(days=6)).astype(str)
    weekly.to_json(expandvars(f"$DIARY_DIR/layers/streaks/{name}.json"), indent=2)
