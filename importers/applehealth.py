# %% Imports

from os import environ, path
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from math import isnan
from glob import glob
from zipfile import ZipFile
import json


# %% Load data

filename = sorted(glob(path.expanduser("~/Downloads/????-??-??-apple-health.zip")))[-1]
print(f"Reading from: '{filename}'")
with ZipFile(filename) as zf:
    root = ET.parse(zf.open("apple_health_export/export.xml")).getroot()


# %% Helpers


def diary_path(*parts: str):
    return path.join(environ["DIARY_DIR"], *parts)


def parse_date(node):
    return node.attrib["endDate"][0:10]


def parse_duration(node, expected_unit="min"):
    if node.attrib["durationUnit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return float(node.attrib["duration"])


def parse_distance(node, name: str, expected_unit="mi"):
    distance_node = node.find(f"*[@type='HKQuantityTypeIdentifierDistance{name}']")
    if distance_node is None:
        return None
    if distance_node.attrib["unit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return float(distance_node.attrib["sum"])


def parse_calories(node, expected_unit="Cal"):
    calories_node = node.find("*[@type='HKQuantityTypeIdentifierActiveEnergyBurned']")
    if calories_node.attrib["unit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return round(float(calories_node.attrib["sum"]))


def parse_indoor(node):
    indoor_node = node.find("*[@key='HKIndoorWorkout']")
    return indoor_node.attrib["value"] == "1"


def sum_by_date(df):
    return df.groupby("date").agg("sum").reset_index()


def gather_records(rtype: str, unit: str, sources: list[str], vtype=float, agg="sum"):
    df = pd.DataFrame(
        {
            "date": node.attrib["endDate"][0:10],
            "value": vtype(node.attrib["value"]),
        }
        for node in root.iterfind(f"./Record[@type='{rtype}']")
        if node.attrib["sourceName"] in sources and node.attrib["unit"] == unit
    )
    series = df.groupby("date").agg(agg)["value"]
    series.index = pd.to_datetime(series.index)
    return series


# %% Running data

new_running = sum_by_date(
    pd.DataFrame(
        {
            "date": parse_date(node),
            "distance": parse_distance(node, "WalkingRunning"),
            "calories": parse_calories(node),
            "duration": parse_duration(node),
        }
        for node in root.iterfind(
            "./Workout[@workoutActivityType='HKWorkoutActivityTypeRunning']"
        )
    )
)


old_running_json = json.load(open(diary_path("misc/2017-12-14-running-data.json")))
old_running = pd.DataFrame(
    (
        {"date": date, "distance": distance}
        for date, distance in old_running_json.items()
    )
)

running = pd.concat([old_running, new_running]).astype({"calories": "Int64"})


# %% Cycling data

mixed_cycling = pd.DataFrame(
    {
        "date": parse_date(node),
        "calories": parse_calories(node),
        "duration": parse_duration(node),
        "distance": parse_distance(node, "Cycling"),
        "indoor": parse_indoor(node),
    }
    for node in root.iterfind(
        "./Workout[@workoutActivityType='HKWorkoutActivityTypeCycling']"
    )
)

indoor_cycling = sum_by_date(
    mixed_cycling[mixed_cycling["indoor"] == True].drop(["distance", "indoor"], axis=1)
)

outdoor_cycling = sum_by_date(
    mixed_cycling[mixed_cycling["indoor"] == False].drop(["indoor"], axis=1)
)


# %% Weight data

new_weight_data = pd.concat(
    {
        "weight": gather_records(
            "HKQuantityTypeIdentifierBodyMass", "lb", ["Withings"], agg="min"
        ),
        "fat": gather_records(
            "HKQuantityTypeIdentifierBodyFatPercentage", "%", ["Withings"], agg="min"
        ),
    },
    axis=1,
)

old_weight_data = pd.read_table(
    diary_path("misc/2024-01-22-old-weights.tsv"),
    parse_dates=["date"],
    index_col="date",
)

weight_data = pd.concat([old_weight_data, new_weight_data])

# %% Weight graph

w = weight_data.dropna()
w["fat_weight"] = w["weight"] * w["fat"]
w = w.reset_index().melt("date", ["weight", "fat_weight"])

sns.lineplot(
    w,
    x="date",
    y="value",
    hue="variable",
)
plt.ylim(0)
plt.show(block=False)


# %% Write TSV files


def write_tsv(df: pd.DataFrame, name: str, precision: dict[str, int] = {}):
    df = df.apply(
        lambda r: {
            k: (
                format(v, f".{precision[k]}f") if k in precision and not isnan(v) else v
            )
            for k, v in r.items()
        },
        axis=1,
        result_type="expand",
    )
    output_filename = diary_path("data", f"{name}.tsv")
    df.to_csv(output_filename, sep="\t", index=False, float_format="%.2f")


write_tsv(running, "running")
write_tsv(indoor_cycling, "indoor-cycling")
write_tsv(outdoor_cycling, "outdoor-cycling")
write_tsv(weight_data.reset_index(), "weight", {"weight": 2, "fat": 3})
