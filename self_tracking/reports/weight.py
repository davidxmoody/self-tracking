import plotly.express as px
import pandas as pd
from typing import cast

import self_tracking.data as d


# %%
w = d.weight().dropna()

w["fat_mass"] = w.weight * w.fat
w["lean_mass"] = w.weight - w.fat_mass

w = w[["fat_mass", "lean_mass"]]

w = cast(pd.DataFrame, w.rolling(7).mean()).dropna()

w_long = w.reset_index().melt(id_vars="date", var_name="type", value_name="value")
w_long = w_long.sort_values("type", ascending=False)

# %%
fig = px.area(w_long, x="date", y="value", color="type")
fig.show()
