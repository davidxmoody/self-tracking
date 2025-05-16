from datetime import date, timedelta
from os.path import expandvars
from pathlib import Path
from typing import cast
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import pandas as pd
from yaspin import yaspin


# %%
fresh_path = Path("~/Downloads/export.zip").expanduser()
export_path = Path("~/.cache/apple-health-export.zip").expanduser()
xml_sub_path = "apple_health_export/export.xml"


def copy_fresh():
    if fresh_path.exists():
        with ZipFile(fresh_path) as zf:
            if xml_sub_path in zf.namelist():
                fresh_path.rename(export_path)
                return True
    return False


def getroot() -> ET.Element:
    with ZipFile(export_path) as zf:
        return ET.parse(zf.open(xml_sub_path)).getroot()


def get_last_full_day(root: ET.Element):
    export_date_node = root.find("./ExportDate")
    if export_date_node is None:
        raise Exception("Could not find export date")
    export_date = date.fromisoformat(export_date_node.attrib["value"][0:10])
    return export_date - timedelta(days=1)


def parse_start(node):
    return pd.to_datetime(node.attrib["startDate"], utc=True).tz_convert(
        "Europe/London"
    )


def parse_duration(node, expected_unit="min"):
    if node.attrib["durationUnit"] != expected_unit:
        raise Exception("Unexpected unit found")
    return float(node.attrib["duration"]) / 60


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


def gather_records(
    root: ET.Element,
    rtype: str,
    unit: str,
    sources: list[str],
    agg="sum",
    fast_date=True,
    utc=True,
):
    df = pd.DataFrame(
        {
            "date": (
                node.attrib["endDate"][0:10]
                if fast_date
                else pd.to_datetime(node.attrib["endDate"], utc=utc).date()
            ),
            "value": float(node.attrib["value"]),
        }
        for node in root.iterfind(f"./Record[@type='HKQuantityTypeIdentifier{rtype}']")
        if node.attrib["sourceName"] in sources and node.attrib["unit"] == unit
    )
    series = cast(pd.Series, df.groupby("date").agg(agg)["value"])
    series.index = pd.to_datetime(series.index)
    return series


def write_tsv(
    df: pd.DataFrame,
    name: str,
    index=True,
    dp: dict[str, int] = {"duration": 4, "distance": 2},
):
    df = df.copy()
    for col, decimals in dp.items():
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: f"{x:.{decimals}f}" if pd.notnull(x) else ""
            )

    df.to_csv(expandvars(f"$DIARY_DIR/data/{name}.tsv"), sep="\t", index=index)
    return len(df)


# %%
def extract_running(root: ET.Element):
    manual_export = pd.read_table(
        expandvars("$DIARY_DIR/data/exports/running-manual.tsv"),
        parse_dates=["date"],
    )
    running_manual = pd.DataFrame(
        {
            "start": (manual_export.date + pd.Timedelta(hours=12)).dt.tz_localize(
                "Europe/London"
            ),
            "duration": manual_export.distance * (9 / 60),
            "distance": manual_export.distance,
            "calories": (manual_export.distance * 110).astype(int),
        }
    )

    garmin_export = pd.read_csv(expandvars("$DIARY_DIR/data/exports/garmin.csv")).query(
        "`Activity Type` == 'Running'"
    )
    running_garmin = pd.DataFrame(
        {
            "start": pd.to_datetime(garmin_export.Date).dt.tz_localize("Europe/London"),
            "duration": pd.to_timedelta(
                garmin_export.Time.replace(r"\.\d*", "", regex=True)
            ).dt.total_seconds()
            / (60 * 60),
            "distance": garmin_export.Distance,
            "calories": garmin_export.Calories.str.replace(",", "").astype(int),
        }
    )

    running_apple = pd.DataFrame(
        {
            "start": parse_start(node),
            "duration": parse_duration(node),
            "distance": parse_distance(node, "WalkingRunning"),
            "calories": parse_calories(node),
        }
        for node in root.iterfind(
            "./Workout[@workoutActivityType='HKWorkoutActivityTypeRunning']"
        )
    )

    running = pd.concat(
        [running_manual, running_garmin, running_apple], ignore_index=True
    ).sort_values("start")

    return write_tsv(running, "workouts/running", index=False)


# %%
def parse_indoor(node):
    indoor_node = node.find("*[@key='HKIndoorWorkout']")
    return indoor_node.attrib["value"] == "1"


def extract_cycling(root: ET.Element):
    cycling_mixed = pd.DataFrame(
        {
            "start": parse_start(node),
            "duration": parse_duration(node),
            "distance": parse_distance(node, "Cycling"),
            "calories": parse_calories(node),
            "indoor": parse_indoor(node),
        }
        for node in root.iterfind(
            "./Workout[@workoutActivityType='HKWorkoutActivityTypeCycling']"
        )
    )

    cycling_indoor = cycling_mixed[cycling_mixed["indoor"] == True].drop(
        ["distance", "indoor"], axis=1
    )

    cycling_outdoor = cycling_mixed[cycling_mixed["indoor"] == False].drop(
        ["indoor"], axis=1
    )

    c1 = write_tsv(cycling_indoor, "workouts/cycling-indoor", index=False)
    c2 = write_tsv(cycling_outdoor, "workouts/cycling", index=False)
    return c1 + c2


# %%
def extract_activity(root: ET.Element):
    activity_sources = ["David’s Apple\xa0Watch"]

    activity = pd.concat(
        {
            "active_calories": gather_records(
                root, "ActiveEnergyBurned", "Cal", activity_sources
            ),
            "basal_calories": gather_records(
                root, "BasalEnergyBurned", "kcal", activity_sources
            ),
        },
        axis=1,
    )

    activity = activity.loc["2017-12-16" : get_last_full_day(root)].round(0).astype(int)

    return write_tsv(activity, "activity")


# %%
def extract_diet(root: ET.Element):
    diet_sources = ["Calorie Counter", "YAZIO", "MyNetDiary"]

    diet = pd.concat(
        {
            "calories": gather_records(
                root,
                "DietaryEnergyConsumed",
                "Cal",
                diet_sources,
                fast_date=False,
            ),
            "protein": gather_records(
                root, "DietaryProtein", "g", diet_sources, fast_date=False
            ),
            "fat": gather_records(
                root, "DietaryFatTotal", "g", diet_sources, fast_date=False
            ),
            "carbs": gather_records(
                root, "DietaryCarbohydrates", "g", diet_sources, fast_date=False
            ),
            "sugar": gather_records(
                root, "DietarySugar", "g", diet_sources, fast_date=False
            ),
            "fiber": gather_records(
                root, "DietaryFiber", "g", diet_sources, fast_date=False
            ),
        },
        axis=1,
    ).astype(int)

    diet = diet.loc[: get_last_full_day(root)]

    return write_tsv(diet, "diet")


# %%
def extract_weight(root: ET.Element):
    weight_sources = ["Withings"]

    weight_new = pd.concat(
        {
            "weight": gather_records(root, "BodyMass", "lb", weight_sources, agg="min"),
            "fat": gather_records(
                root, "BodyFatPercentage", "%", weight_sources, agg="min"
            ),
        },
        axis=1,
    )

    weight_manual = pd.read_table(
        expandvars("$DIARY_DIR/data/exports/weight-manual.tsv"),
        parse_dates=["date"],
        index_col="date",
    )

    weight = pd.concat([weight_manual, weight_new])

    return write_tsv(weight, "weight", dp={"weight": 2, "fat": 3})


# %%
def extract_meditation(root: ET.Element):
    df = pd.DataFrame(
        {
            "start": parse_start(node),
            "duration": (
                pd.to_datetime(node.attrib["endDate"])
                - pd.to_datetime(node.attrib["startDate"])
            ).total_seconds()
            / (60 * 60),
        }
        for node in root.iterfind(
            "./Record[@type='HKCategoryTypeIdentifierMindfulSession']"
        )
    )

    df = df.loc[df.duration >= (1 / 60)]

    return write_tsv(df, "meditation", index=False)


# %%
def extract_sleep(root: ET.Element):
    sleep_sources = ["David’s Apple\xa0Watch"]

    sleep = pd.DataFrame(
        {
            "source": x.attrib["sourceName"],
            "start": pd.to_datetime(x.attrib["startDate"]),
            "end": pd.to_datetime(x.attrib["endDate"]),
            "subtype": x.attrib["value"][28:],
        }
        for x in root.iterfind(
            "./Record[@type='HKCategoryTypeIdentifierSleepAnalysis']"
        )
    )

    # Note: A lot of potential data in an older format is being discarded here.
    sleep = sleep.loc[
        sleep.source.isin(sleep_sources)
        & ~sleep.subtype.isin(["AsleepUnspecified", "InBed"])
    ]

    sleep["subtype"] = sleep.subtype.str.replace("Asleep", "")

    sleep["duration"] = (sleep.end - sleep.start).dt.total_seconds() / (60 * 60)

    sleep["date"] = pd.to_datetime((sleep.end + timedelta(hours=8)).dt.date)

    columns = ["Deep", "Core", "REM", "Awake"]

    sleep_pivot = sleep.pivot_table(
        index="date", columns="subtype", values="duration", aggfunc="sum"
    ).fillna(0.0)[columns]

    return write_tsv(sleep_pivot, "sleep", dp={c: 4 for c in columns})


# %%
def main():
    with yaspin(text="Apple Health") as spinner:
        if not copy_fresh():
            spinner.text += " (skipped)"
            spinner.ok("→")
            return

        count = 0
        root = getroot()
        count += extract_running(root)
        count += extract_cycling(root)
        count += extract_activity(root)
        count += extract_diet(root)
        count += extract_weight(root)
        count += extract_meditation(root)
        count += extract_sleep(root)

        spinner.text += f" ({count} total records)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
