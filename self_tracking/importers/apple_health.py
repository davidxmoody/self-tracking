from datetime import date, timedelta
from self_tracking.dirs import diary_dir, downloads_dir, cache_dir
from typing import cast
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import pandas as pd
from yaspin import yaspin

# %%
fresh_path = downloads_dir / "export.zip"
export_path = cache_dir / "apple-health-export.zip"
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
):
    df = pd.DataFrame(
        {
            "end": node.attrib["endDate"],
            "value": float(node.attrib["value"]),
        }
        for node in root.iterfind(f"./Record[@type='HKQuantityTypeIdentifier{rtype}']")
        if node.attrib["sourceName"] in sources and node.attrib["unit"] == unit
    )
    # The export writes timestamps in whatever timezone the phone was in at
    # export time, so normalise to London before taking the date. Otherwise
    # records near midnight flip between days depending on when you export.
    df["date"] = (
        pd.to_datetime(df.end, format="%Y-%m-%d %H:%M:%S %z", utc=True)
        .dt.tz_convert("Europe/London")
        .dt.tz_localize(None)
        .dt.normalize()
    )
    return cast(pd.Series, df.groupby("date").agg(agg)["value"])


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

    df.to_csv(diary_dir / f"data/{name}.tsv", sep="\t", index=index)
    return len(df)


# %%
def extract_running(root: ET.Element):
    manual_export = pd.read_table(
        diary_dir / "data/exports/running-manual.tsv",
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

    garmin_export = pd.read_csv(diary_dir / "data/exports/garmin.csv").query(
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
def extract_cycling(root: ET.Element):
    cycling_mixed = pd.DataFrame(
        {
            "start": parse_start(node),
            "duration": parse_duration(node),
            "distance": parse_distance(node, "Cycling"),
            "calories": parse_calories(node),
        }
        for node in root.iterfind(
            "./Workout[@workoutActivityType='HKWorkoutActivityTypeCycling']"
        )
    )

    is_indoor = cycling_mixed["distance"].isna() | (cycling_mixed["distance"] == 0)

    cycling_indoor = cycling_mixed[is_indoor].drop(["distance"], axis=1)

    cycling_outdoor = cycling_mixed[~is_indoor]

    c1 = write_tsv(cycling_indoor, "workouts/cycling-indoor", index=False)
    c2 = write_tsv(cycling_outdoor, "workouts/cycling", index=False)
    return c1 + c2


# %%
def extract_activity(root: ET.Element):
    activity_sources = ["David’s Apple\xa0Watch"]

    activity = pd.DataFrame(
        {
            "active_calories": gather_records(
                root, "ActiveEnergyBurned", "Cal", activity_sources
            ),
        }
    )

    activity = activity.loc["2017-12-16" : get_last_full_day(root)].round(0).astype(int)

    return write_tsv(activity, "activity")


# %%
def extract_diet(root: ET.Element):
    diet_sources = ["Calorie Counter", "Yazio", "MyNetDiary"]

    diet = pd.concat(
        {
            "calories": gather_records(
                root,
                "DietaryEnergyConsumed",
                "Cal",
                diet_sources,
            ),
            "protein": gather_records(
                root, "DietaryProtein", "g", diet_sources
            ),
            "fat": gather_records(
                root, "DietaryFatTotal", "g", diet_sources
            ),
            "carbs": gather_records(
                root, "DietaryCarbohydrates", "g", diet_sources
            ),
            "sugar": gather_records(
                root, "DietarySugar", "g", diet_sources
            ),
            "fiber": gather_records(
                root, "DietaryFiber", "g", diet_sources
            ),
        },
        axis=1,
    ).astype(int)

    diet = diet.loc[: get_last_full_day(root)]

    return write_tsv(diet, "diet")


# %%
FOOD_NUTRIENTS = {
    "DietaryEnergyConsumed": ("kcal", "Cal"),
    "DietaryFatTotal": ("fat", "g"),
    "DietaryFatSaturated": ("sat_fat", "g"),
    "DietaryCarbohydrates": ("carbs", "g"),
    "DietarySugar": ("sugar", "g"),
    "DietaryFiber": ("fibre", "g"),
    "DietaryProtein": ("protein", "g"),
    "DietarySodium": ("sodium", "mg"),
}

# MyNetDiary writes every food at a fixed time for its meal. Lunch moved from
# 12:00 to 11:00 around April 2025.
MYNETDIARY_MEALS = {
    "08:00": "breakfast",
    "11:00": "lunch",
    "12:00": "lunch",
    "15:00": "snacks",
    "18:00": "dinner",
}


def parse_food(node: ET.Element):
    food_type = node.find("./MetadataEntry[@key='HKFoodType']")
    food = {
        "start": parse_start(node),
        "desc": food_type.attrib["value"].strip() if food_type is not None else "",
    }
    for record in node.iterfind("./Record"):
        rtype = record.attrib["type"].removeprefix("HKQuantityTypeIdentifier")
        if rtype in FOOD_NUTRIENTS:
            col, unit = FOOD_NUTRIENTS[rtype]
            if record.attrib["unit"] != unit:
                raise Exception("Unexpected unit found")
            food[col] = float(record.attrib["value"])
    return food


def extract_mynetdiary(root: ET.Element):
    df = pd.DataFrame(
        parse_food(node)
        for node in root.iterfind(
            "./Correlation[@type='HKCorrelationTypeIdentifierFood'][@sourceName='MyNetDiary']"
        )
    )

    slot = df.start.dt.strftime("%H:%M")
    unknown = set(slot) - set(MYNETDIARY_MEALS)
    if unknown:
        raise Exception(f"Unexpected MyNetDiary meal times: {sorted(unknown)}")

    df["date"] = df.start.dt.tz_localize(None).dt.normalize()
    df["meal"] = slot.map(MYNETDIARY_MEALS)
    df["kcal"] = df.kcal.round().astype(int)
    df["salt"] = df.sodium * 2.5 / 1000
    df = df.loc[df.date <= pd.Timestamp(get_last_full_day(root))]

    meal_order = {"breakfast": 0, "lunch": 1, "dinner": 2, "snacks": 3}
    df = df.assign(order=df.meal.map(meal_order)).sort_values(
        ["date", "order"], kind="stable"
    )

    columns = ["date", "meal", "desc", "kcal", "fat", "sat_fat", "carbs", "sugar", "fibre", "protein", "salt"]
    df["date"] = df.date.dt.strftime("%Y-%m-%d")
    for col in columns[4:]:
        df[col] = df[col].round(3)

    return write_tsv(df[columns], "mynetdiary", index=False, dp={})


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
        diary_dir / "data/exports/weight-manual.tsv",
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
        count += extract_mynetdiary(root)
        count += extract_weight(root)
        count += extract_meditation(root)
        count += extract_sleep(root)

        spinner.text += f" ({count} total records)"
        spinner.ok("✔")


if __name__ == "__main__":
    main()
