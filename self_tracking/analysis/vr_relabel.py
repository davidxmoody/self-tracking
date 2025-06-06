from pathlib import Path
from typing import Any, cast
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import pandas as pd
import self_tracking.data as d
import plotly.express as px


# %%
def getroot() -> ET.Element:
    with ZipFile(Path("~/.cache/apple-health-export.zip").expanduser()) as zf:
        return ET.parse(zf.open("apple_health_export/export.xml")).getroot()


root = getroot()


# %%
activity = pd.DataFrame(
    {
        "start": node.attrib["startDate"],
        "end": node.attrib["endDate"],
        "value": float(node.attrib["value"]),
    }
    for node in root.iterfind(
        f"./Record[@type='HKQuantityTypeIdentifierActiveEnergyBurned']"
    )
    if node.attrib["sourceName"] == "David’s Apple\xa0Watch"
    and node.attrib["unit"] == "Cal"
)


# %%
atracker = d.atracker_events()
gaming = atracker.loc[atracker.category == "gaming", ["start", "duration"]]


# All Apple Health export data has the same timezone as the date it was exported
tz = pd.to_datetime(cast(Any, activity.iloc[0, 0])).tz

# It's too slow to parse all the activity dates so convert the event ones to the same string format
gaming["start_str"] = gaming.start.dt.tz_convert(tz).dt.strftime("%Y-%m-%d %H:%M:%S %z")
gaming["end_str"] = (
    (gaming.start + pd.to_timedelta(gaming.duration, unit="h"))
    .dt.tz_convert(tz)
    .dt.strftime("%Y-%m-%d %H:%M:%S %z")
)


# %%
def calculate_activity(row):
    subset = activity.loc[
        (activity.end > row.start_str) & (activity.start < row.end_str)
    ]
    total = subset.value.sum()
    print(row.start_str, total)
    return total


gaming["activity"] = gaming.apply(calculate_activity, axis=1)


# %%
gaming.to_csv("gaming.tsv", sep="\t", index=False)


# %%
px.scatter(gaming, x="duration", y="activity")


# %%
gaming["activity_rate"] = gaming.activity / gaming.duration


# %%
non_zero_gaming = gaming.loc[gaming.activity_rate > 0]

fig = px.scatter(
    non_zero_gaming,
    x="start",
    y="activity_rate",
    color="activity_rate",
    color_continuous_scale="Bluered",
    color_continuous_midpoint=100,
    range_color=[0, 400],
)

fig.update_layout(
    title="Gaming session activity ratios",
    xaxis_title="Date",
    yaxis_title="Active calories per hour",
    yaxis=dict(range=[0, 400]),
    xaxis=dict(range=[non_zero_gaming["start"].min(), non_zero_gaming["start"].max()]),
)

fig.update_coloraxes(showscale=False)

fig
