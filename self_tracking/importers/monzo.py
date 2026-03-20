import pandas as pd
from self_tracking.dirs import diary_dir

output_dir = diary_dir / "data/money"
output_dir.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(diary_dir / "data/exports/monzo.csv")

df["date"] = pd.to_datetime(df["Date"], format="%d/%m/%Y")
df["time"] = df["Time"]
df["amount"] = df["Amount"].astype(float)

df = df.sort_values(["date", "time"])
df["balance"] = df["amount"].cumsum()

# Keep last balance per day
df = df.groupby("date").last().reset_index()[["date", "balance"]]

df["balance"] = df["balance"].round(2)

df.to_csv(output_dir / "monzo.tsv", sep="\t", index=False)
