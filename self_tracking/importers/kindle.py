from os.path import expandvars
import zipfile
import pandas as pd


zip_path = expandvars("$DIARY_DIR/data/exports/kindle.zip")
filepaths = {
    "reading": "Kindle.ReadingInsights/datasets/Kindle.reading-insights-sessions_with_adjustments/Kindle.reading-insights-sessions_with_adjustments.csv",
    "whispersync": "Digital.Content.Whispersync/whispersync.csv",
}
dfs = {}

with zipfile.ZipFile(zip_path, "r") as zf:
    for name, filepath in filepaths.items():
        with zf.open(filepath) as file:
            dfs[name] = pd.read_csv(file)


book_titles = (
    dfs["whispersync"].drop_duplicates("ASIN").set_index("ASIN")["Product Name"]
)


df = pd.DataFrame(
    {
        "date": pd.to_datetime(dfs["reading"].start_time, format="ISO8601", utc=True)
        .dt.tz_convert("Europe/London")
        .dt.date,
        "duration": dfs["reading"].total_reading_milliseconds / (1000 * 60 * 60),
        "title": dfs["reading"]
        .ASIN.map(book_titles)
        .fillna("Not Available")
        .str.replace(r"^Penguin Readers Level \d: ", "", regex=True)
        .str.replace(r" - Updated Edition", "", regex=True)
        .str.replace(r", The - .*", "", regex=True)
        .str.replace(r"\(.*?\)", "", regex=True)
        .str.replace(r":.*$", "", regex=True)
        .str.strip(),
    }
)

df = df.groupby(["date", "title"]).sum().reset_index()

df = df.loc[df.duration > (1 / 60)]

df.to_csv(
    expandvars("$DIARY_DIR/data/kindle.tsv"),
    sep="\t",
    index=False,
    float_format="%.4f",
)
