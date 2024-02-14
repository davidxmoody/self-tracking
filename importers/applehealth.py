# %% Imports

from datetime import date, timedelta
from glob import glob
from math import isnan
from os.path import expandvars
from typing import cast
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd


# %% Load

filepath = sorted(glob(expandvars("$HOME/Downloads/????-??-??-apple-health.zip")))[-1]
with ZipFile(filepath) as zf:
    root = ET.parse(zf.open("apple_health_export/export.xml")).getroot()

export_date_node = root.find("./ExportDate")
if export_date_node is None:
    raise Exception("Could not find export date")
export_date = date.fromisoformat(export_date_node.attrib["value"][0:10])
last_full_day = export_date - timedelta(days=1)


# %% Helpers


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


# %% Running

running_manual = read_table_with_date_index(
    expandvars("$DIARY_DIR/misc/2024-02-14-old-running.tsv")
)

running_garmin = pd.read_csv(
    expandvars("$DIARY_DIR/misc/2024-02-14-garmin-export.csv")
).query("`Activity Type` == 'Running'")

running_garmin = pd.DataFrame(
    {
        "date": pd.to_datetime(running_garmin.Date.str[0:10]),
        "distance": running_garmin.Distance,
        "calories": running_garmin.Calories.str.replace(",", "").astype(int),
        "duration": running_garmin.Time.replace(r"\.\d*", "", regex=True).apply(
            lambda v: sum(int(x) * 60 ** (1 - i) for i, x in enumerate(v.split(":")))
        ),
    }
).set_index("date")

running_apple = sum_by_date(
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

running = (
    pd.concat([running_manual, running_garmin, running_apple])
    .astype({"calories": "Int64"})
    .sort_index()
)


# %% Cycling

cycling_mixed = pd.DataFrame(
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

cycling_indoor = sum_by_date(
    cycling_mixed[cycling_mixed["indoor"] == True].drop(["distance", "indoor"], axis=1)
)

cycling_outdoor = sum_by_date(
    cycling_mixed[cycling_mixed["indoor"] == False].drop(["indoor"], axis=1)
)


# %% Activity

activity_sources = ["David’s Apple\xa0Watch"]

activity = pd.concat(
    {
        "active_calories": gather_records(
            "ActiveEnergyBurned", "Cal", activity_sources
        ),
        "basal_calories": gather_records("BasalEnergyBurned", "kcal", activity_sources),
    },
    axis=1,
)

activity = activity.loc["2017-12-16":last_full_day].round(0).astype(int)


# %% Diet

diet_sources = ["Calorie Counter", "YAZIO", "MyNetDiary"]

diet = pd.concat(
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

diet = diet.loc[:last_full_day]


# %% Weight

weight_sources = ["Withings"]

weight_new = pd.concat(
    {
        "weight": gather_records("BodyMass", "lb", weight_sources, agg="min"),
        "fat": gather_records("BodyFatPercentage", "%", weight_sources, agg="min"),
    },
    axis=1,
)

weight_old = read_table_with_date_index(
    expandvars("$DIARY_DIR/misc/2024-01-22-old-weights.tsv")
)

weight = pd.concat([weight_old, weight_new])


# %% Meditation


def parse_mindful_minutes(node):
    start = pd.to_datetime(node.attrib["startDate"])
    end = pd.to_datetime(node.attrib["endDate"])
    return round((end - start).total_seconds() / 60)


meditation = sum_by_date(
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


# %% Sleep

sleep_sources = ["David’s Apple\xa0Watch"]

sleep = pd.DataFrame(
    {
        "source": x.attrib["sourceName"],
        "start": pd.to_datetime(x.attrib["startDate"]),
        "end": pd.to_datetime(x.attrib["endDate"]),
        "subtype": x.attrib["value"][28:],
    }
    for x in root.iterfind("./Record[@type='HKCategoryTypeIdentifierSleepAnalysis']")
)

# Note: A lot of potential data in an older format is being discarded here.
sleep = sleep.loc[
    sleep.source.isin(sleep_sources)
    & ~sleep.subtype.isin(["AsleepUnspecified", "InBed"])
]

sleep["subtype"] = sleep.subtype.str.replace("Asleep", "")

sleep["duration"] = (sleep.end - sleep.start).dt.total_seconds()

sleep["date"] = pd.to_datetime((sleep.end + timedelta(hours=8)).dt.date)

sleep_pivot = sleep.pivot_table(
    index="date", columns="subtype", values="duration", aggfunc="sum"
).astype(int)[["Deep", "Core", "REM", "Awake"]]


# %% Write TSV files


def write_tsv(df: pd.DataFrame, name: str, precisions: dict[str, int] = {}):
    df = df.copy()
    for col, p in precisions.items():
        df[col] = df[col].apply(
            lambda v: "" if isnan(float(v)) else format(float(v), f".{p}f")
        )

    output_filename = expandvars(f"$DIARY_DIR/data/{name}.tsv")
    df.to_csv(output_filename, sep="\t", float_format="%.2f")


write_tsv(running, "running")
write_tsv(cycling_indoor, "cycling-indoor")
write_tsv(cycling_outdoor, "cycling-outdoor")
write_tsv(weight, "weight", {"fat": 3})
write_tsv(activity, "activity")
write_tsv(diet, "diet")
write_tsv(meditation, "meditation")
write_tsv(sleep_pivot, "sleep")
