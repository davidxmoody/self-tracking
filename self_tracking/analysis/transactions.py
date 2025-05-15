import pandas as pd
from pathlib import Path
from os.path import expandvars


# %%
input_files = [
    Path(expandvars("$DIARY_DIR/misc/2025-04-30-santander-transactions.txt")),
    Path(expandvars("$DIARY_DIR/misc/2020-04-13-santander-transactions.txt")),
]

transactions = []

for input_file in input_files:
    with open(input_file, encoding="cp1252") as f:
        lines = [line.strip() for line in f]
        for i in range(4, len(lines), 5):
            transactions.append(
                {
                    "date": pd.to_datetime(lines[i].split(": ")[1], format="%d/%m/%Y"),
                    "name": lines[i + 1].split(": ")[1],
                    "amount": float(lines[i + 2].split(": ")[1].removesuffix(" GBP")),
                    "balance": float(lines[i + 3].split(": ")[1].removesuffix(" GBP")),
                }
            )

df = pd.DataFrame(transactions).sort_values("date")
