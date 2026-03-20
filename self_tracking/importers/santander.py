import pandas as pd
from self_tracking.dirs import diary_dir

output_dir = diary_dir / "data/money"
output_dir.mkdir(parents=True, exist_ok=True)

input_files = [
    diary_dir / "misc/2020-04-13-santander-transactions.txt",
    diary_dir / "misc/2025-04-30-santander-transactions.txt",
]

transactions = []

for input_file in input_files:
    with open(input_file, encoding="cp1252") as f:
        lines = [line.strip() for line in f]
        for i in range(4, len(lines), 5):
            transactions.append(
                {
                    "date": pd.to_datetime(lines[i].split(": ")[1], format="%d/%m/%Y"),
                    "balance": float(lines[i + 3].split(": ")[1].removesuffix(" GBP")),
                }
            )

df = pd.DataFrame(transactions).sort_values("date")

# Keep last balance per day
df = df.groupby("date").last().reset_index()

df.to_csv(output_dir / "santander.tsv", sep="\t", index=False)
