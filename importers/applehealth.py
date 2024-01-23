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

filename = sorted(glob(path.expanduser("~/Downloads/????-??-??-apple-health.zip")))[-1]
print(f"Reading from: '{filename}'")
with ZipFile(filename) as zf:
    root = ET.parse(zf.open("apple_health_export/export.xml")).getroot()


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


new_weights = pd.DataFrame(
    node.attrib
    for node in root.iterfind("./Record[@type='HKQuantityTypeIdentifierBodyMass']")
).sort_values("endDate")
new_weights["date"] = pd.to_datetime(new_weights["endDate"].str.slice(0, 10))
new_weights = new_weights[new_weights["sourceName"] == "Withings"]
new_weights = new_weights.drop_duplicates(subset="date", keep="last").sort_values(
    "date"
)
if (new_weights["unit"] != "lb").any():
    raise Exception("Unexpected unit found")
new_weights["weight"] = new_weights["value"].astype(float)
new_weights = new_weights[["date", "weight"]].reset_index(drop=True)

body_fat = pd.DataFrame(
    node.attrib
    for node in root.iterfind(
        "./Record[@type='HKQuantityTypeIdentifierBodyFatPercentage']"
    )
).sort_values("endDate")
body_fat["date"] = pd.to_datetime(body_fat["endDate"].str.slice(0, 10))
body_fat = body_fat[body_fat["sourceName"] == "Withings"]
body_fat = body_fat.drop_duplicates(subset="date", keep="last").sort_values("date")
if (body_fat["unit"] != "%").any():
    raise Exception("Unexpected unit found")
body_fat["fat"] = body_fat["value"].astype(float)
body_fat = body_fat[["date", "fat"]].reset_index(drop=True)

new_weights = pd.merge(new_weights, body_fat, how="left")

old_weights = pd.read_table(
    diary_path("misc/2024-01-22-old-weights.tsv"), parse_dates=["date"]
)

weights = pd.concat([old_weights, new_weights]).reset_index(drop=True)

write_tsv(weights, "weight", {"weight": 2, "fat": 3})

# weights["fat_weight"] = weights["weight"] * weights["fat"]

# sns.lineplot(
#     weights.melt("date", ["weight", "fat_weight"], "col"),
#     x="date",
#     y="value",
#     hue="col",
# )
# plt.ylim(0)
# plt.show(block=False)
