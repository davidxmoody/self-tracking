from glob import glob
from os.path import expandvars
from typing import Any, cast
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import pandas as pd
import self_tracking.data as d


# %%
def getroot() -> ET.Element:
    fp = sorted(glob(expandvars("$HOME/Downloads/????-??-??-apple-health.zip")))[-1]
    with ZipFile(fp) as zf:
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
gaming.to_csv(expandvars("gaming.tsv"), sep="\t", index=False)


# %%
import plotly.express as px

px.scatter(gaming, x="duration", y="activity")


# %%
gaming["activity_rate"] = gaming.activity / gaming.duration


# %%
gaming = gaming.loc[gaming.activity < 500]
