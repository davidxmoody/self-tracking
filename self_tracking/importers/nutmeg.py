import json
import pandas as pd
from self_tracking.dirs import diary_dir

output_dir = diary_dir / "data/money"
output_dir.mkdir(parents=True, exist_ok=True)

with open(diary_dir / "data/exports/nutmeg.json") as f:
    data = json.load(f)

df = pd.DataFrame(data["points"])[["date", "overallValue"]]
df.columns = ["date", "balance"]
df["date"] = pd.to_datetime(df["date"])
df["balance"] = df["balance"].round(2)

# Keep last balance per day (should already be unique, but just in case)
df = df.groupby("date").last().reset_index()

df.to_csv(output_dir / "nutmeg.tsv", sep="\t", index=False)
