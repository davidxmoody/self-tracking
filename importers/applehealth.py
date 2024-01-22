from os import environ, path
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np

tree = ET.parse(path.expanduser("~/Downloads/apple_health_export/export.xml"))
root = tree.getroot()

# Note: Cannot use root.iter() due to duplicate records in Correlation tags
records = pd.DataFrame(x.attrib for x in root if x.tag == "Record")


def diary_path(*parts: str):
    return path.join(environ["DIARY_DIR"], *parts)


def parse_date(node):
    return node.attrib["endDate"][0:10]


def parse_duration(node, expected_unit="min"):
    if node.attrib["durationUnit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return float(node.attrib["duration"])


def parse_distance(node, expected_unit="mi"):
    [distance_node] = [
        n
        for n in [
            node.find("*[@type='HKQuantityTypeIdentifierDistanceWalkingRunning']"),
            node.find("*[@type='HKQuantityTypeIdentifierDistanceCycling']"),
        ]
        if n is not None
    ]
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
            "distance": parse_distance(node),
            "calories": parse_calories(node),
            "duration": parse_duration(node),
        }
        for node in root.iterfind(
            "./Workout[@workoutActivityType='HKWorkoutActivityTypeRunning']"
        )
    ).astype({"calories": "Int64"})
)


old_running_json = json.load(open(diary_path("misc/2017-12-14-running-data.json")))
old_running = pd.DataFrame(
    (
        {"date": date, "distance": distance}
        for date, distance in old_running_json.items()
    )
)

running = pd.concat([old_running, new_running])


mixed_cycling = pd.DataFrame(
    {
        "date": parse_date(node),
        "calories": parse_calories(node),
        "duration": parse_duration(node),
        "distance": parse_distance(node),
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

print(running.to_csv(sep="\t", index=False, float_format="%.2f"))
