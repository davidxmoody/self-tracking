# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.1
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# ## Imports


# %% jupyter={"source_hidden": true}
from os.path import expandvars
import pandas as pd


# %% [markdown]
# ## Load Kindle data


# %% jupyter={"source_hidden": true}
df = pd.read_table(expandvars("$DIARY_DIR/data/kindle.tsv"), parse_dates=["date"])


# %%
df.groupby("title").date.apply(lambda x: x.diff().max()).sort_values()
