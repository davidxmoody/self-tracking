from os.path import expanduser
import xml.etree.ElementTree as ET
import pandas as pd

tree = ET.parse(expanduser("~/Downloads/apple_health_export/export.xml"))
root = tree.getroot()

# Note: Cannot use root.iter() due to duplicate records in Correlation tags
records = pd.DataFrame(x.attrib for x in root if x.tag == "Record")


def parse_date(node):
    return node.attrib["endDate"][0:10]


def parse_duration(node, expected_unit="min"):
    if node.attrib["durationUnit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return round(float(node.attrib["duration"]), 2)


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
    return round(float(distance_node.attrib["sum"]), 2)


def parse_calories(node, expected_unit="Cal"):
    calories_node = node.find("*[@type='HKQuantityTypeIdentifierActiveEnergyBurned']")
    if calories_node.attrib["unit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return round(float(calories_node.attrib["sum"]))


def parse_indoor(node):
    indoor_node = node.find("*[@key='HKIndoorWorkout']")
    return indoor_node.attrib["value"] == "1"


def sum_by_date(df):
    return df.groupby("date").agg("sum")


running = sum_by_date(
    pd.DataFrame(
        {
            "date": parse_date(node),
            "calories": parse_calories(node),
            "duration": parse_duration(node),
            "distance": parse_distance(node),
        }
        for node in root.iterfind(
            "./Workout[@workoutActivityType='HKWorkoutActivityTypeRunning']"
        )
    )
)


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
