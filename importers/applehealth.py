# %% Imports

from glob import glob
from math import isnan
from os import environ, path
from typing import cast
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd


# %% Load data

filename = sorted(glob(path.expanduser("~/Downloads/????-??-??-apple-health.zip")))[-1]
with ZipFile(filename) as zf:
    root = ET.parse(zf.open("apple_health_export/export.xml")).getroot()


# %% Helpers


def diary_path(*parts: str):
    return path.join(environ["DIARY_DIR"], *parts)


def parse_date(node):
    return pd.to_datetime(node.attrib["endDate"][0:10])


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
    return cast(pd.DataFrame, df.groupby("date").agg("sum"))


def gather_records(rtype: str, unit: str, sources: list[str], agg="sum"):
    df = pd.DataFrame(
        {
            "date": node.attrib["endDate"][0:10],
            "value": float(node.attrib["value"]),
        }
        for node in root.iterfind(f"./Record[@type='HKQuantityTypeIdentifier{rtype}']")
        if node.attrib["sourceName"] in sources and node.attrib["unit"] == unit
    )
    series = cast(pd.Series, df.groupby("date").agg(agg)["value"])
    series.index = pd.to_datetime(series.index)
    return series


def read_table_with_date_index(filename: str):
    return pd.read_table(filename, parse_dates=["date"], index_col="date")


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

old_running = read_table_with_date_index(diary_path("misc/2024-01-25-old-running.tsv"))

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


# %% Activity data

activity_sources = ["David’s Apple\xa0Watch"]

activity_data = pd.concat(
    {
        "active_calories": gather_records(
            "ActiveEnergyBurned", "Cal", activity_sources
        ),
        "basal_calories": gather_records("BasalEnergyBurned", "kcal", activity_sources),
    },
    axis=1,
)

activity_data = cast(pd.DataFrame, activity_data["2017-12-16":].round(0).astype(int))


# %% Diet data

diet_sources = ["Calorie Counter", "YAZIO"]

diet_data = pd.concat(
    {
        "calories": gather_records("DietaryEnergyConsumed", "Cal", diet_sources),
        "protein": gather_records("DietaryProtein", "g", diet_sources),
        "fat": gather_records("DietaryFatTotal", "g", diet_sources),
        "carbs": gather_records("DietaryCarbohydrates", "g", diet_sources),
        "sugar": gather_records("DietarySugar", "g", diet_sources),
        "fiber": gather_records("DietaryFiber", "g", diet_sources),
    },
    axis=1,
).astype(int)


# %% Weight data

weight_sources = ["Withings"]

new_weight_data = pd.concat(
    {
        "weight": gather_records("BodyMass", "lb", weight_sources, agg="min"),
        "fat": gather_records("BodyFatPercentage", "%", weight_sources, agg="min"),
    },
    axis=1,
)

old_weight_data = read_table_with_date_index(
    diary_path("misc/2024-01-22-old-weights.tsv")
)

weight_data = pd.concat([old_weight_data, new_weight_data])


# %% Meditation data


def parse_mindful_minutes(node):
    start = pd.to_datetime(node.attrib["startDate"])
    end = pd.to_datetime(node.attrib["endDate"])
    return round((end - start).total_seconds() / 60)


meditation_data = sum_by_date(
    pd.DataFrame(
        {
            "date": parse_date(node),
            "mindful_minutes": parse_mindful_minutes(node),
        }
        for node in root.iterfind(
            "./Record[@type='HKCategoryTypeIdentifierMindfulSession']"
        )
    )
)


# %% Write TSV files


def write_tsv(df: pd.DataFrame, name: str, precisions: dict[str, int] = {}):
    df = df.copy()
    for col, p in precisions.items():
        df[col] = df[col].apply(
            lambda v: "" if isnan(float(v)) else format(float(v), f".{p}f")
        )

    output_filename = diary_path("data", f"{name}.tsv")
    df.to_csv(output_filename, sep="\t", float_format="%.2f")


write_tsv(running, "running")
write_tsv(indoor_cycling, "indoor-cycling")
write_tsv(outdoor_cycling, "outdoor-cycling")
write_tsv(weight_data, "weight", {"fat": 3})
write_tsv(activity_data, "activity")
write_tsv(diet_data, "diet")
write_tsv(meditation_data, "meditation")
