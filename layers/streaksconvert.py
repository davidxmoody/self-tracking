# %% Imports

import json
import pandas as pd
from os.path import basename, expandvars
from glob import glob


# %% Load


files = glob(expandvars("$DIARY_DIR/data/streaks/*.json"))

dfs = []

for filename in files:
    name = basename(filename)[:-5]
    with open(filename) as file:
        data = json.load(file)

    dfs.append(
        pd.DataFrame(
            {
                "date": pd.to_datetime(list(data.keys())),
                "name": name,
                "value": data.values(),
            }
        )
    )

df = pd.concat(dfs).sort_values(["date", "name"]).reset_index(drop=True)


# %% Write

df.to_csv(expandvars("$DIARY_DIR/data/streaks.tsv"), sep="\t", index=False)
