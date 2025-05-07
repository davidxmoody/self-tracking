from os.path import expandvars
import zipfile
import pandas as pd
import self_tracking.data as d


# %%
start_date = "2021-02-08"  # Inclusive, date started tracking audiobooks as reading
end_date = "2025-03-30"  # Exclusive, date started tracking separate audiobook category


# %%
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


kindle = pd.DataFrame(
    {
        "start": pd.to_datetime(dfs["reading"].start_time, format="ISO8601", utc=True)
        .dt.tz_convert("Europe/London")
        .dt.round("1s"),
        "duration": dfs["reading"].total_reading_milliseconds / (1000 * 60 * 60),
        "title": dfs["reading"]
        .ASIN.map(book_titles)
        .fillna("Not Available")
        .str.replace(r"^Penguin Readers Level \d: ", "", regex=True)
        .str.replace(r": Book (\d+):", r" \1:", regex=True)
        .str.replace(r" - Updated Edition", "", regex=True)
        .str.replace(r", The - .*", "", regex=True)
        .str.replace(r"\(.*?\)", "", regex=True)
        .str.replace(r":.*$", "", regex=True)
        .str.strip(),
    }
)

kindle = kindle.loc[kindle.duration > (1 / 60)]

kindle = kindle.loc[(kindle.start >= start_date) & (kindle.start < end_date)]

kindle["date"] = pd.to_datetime((kindle.start - pd.Timedelta(hours=4)).dt.date)


# %%
zip_path = expandvars("$DIARY_DIR/data/exports/audible.zip")

with zipfile.ZipFile(zip_path, "r") as zf:
    with zf.open("Audible.Listening/Account Holder/Listening.csv") as file:
        audible = pd.read_csv(file)

audible = audible.dropna()

audible = pd.DataFrame(
    {
        "date": pd.to_datetime(audible["Start Date"]),
        "duration": audible["Event Duration Milliseconds"] / (1000 * 60 * 60),
        "title": audible["Product Name"]
        .str.replace(r"\(.*?\)", "", regex=True)
        .str.replace(r"^(?!Ep)([^:]+):.*", r"\1", regex=True)
        .str.strip()
        .str.replace(r", Book \d$", "", regex=True),
    }
)

audible = audible.loc[audible.duration > (1 / 60)]

audible = audible.loc[(audible.date >= start_date) & (audible.date < end_date)]


# %%
atracker = d.atracker_events()

reading = atracker.loc[atracker.category == "reading"]
reading = reading.loc[(reading.date >= start_date) & (reading.date < end_date)]

# audible["details"] = audible.apply(
#     lambda row: f"{row.duration:.2f} {row.title}", axis=1
# )

# kindle["details"] = kindle.apply(
#     lambda row: f"{row.start.strftime("%H:%M")} {row.duration:.2f} {row.title}", axis=1
# )


# %%
audible = audible.loc[~audible.title.str.contains("Harry Potter")]


# %%
audible = audible.iloc[::-1]
kindle = kindle.iloc[::-1]


# %%
sums = []

for date in reading.date.unique():
    r = reading.loc[reading.date == date]
    a = audible.loc[audible.date == date]
    k = kindle.loc[kindle.date == date]

    rsize = r.shape[0]
    rsum = r.duration.sum()
    asum = a.duration.sum()
    ksum = k.duration.sum()

    sums.append([date, rsize, rsum, asum, ksum])

df = pd.DataFrame(sums)
df.columns = ["date", "rsize", "rsum", "asum", "ksum"]
df = df.set_index("date")

df["err"] = df.rsum - df.asum - df.ksum

adaily = d.atracker()
df["social"] = df.index.map(adaily.social)


# %%
titles = (
    pd.concat([kindle[["date", "title"]], audible[["date", "title"]]])
    .groupby("date")
    .title.apply(lambda x: set(x))
)

df["titles"] = df.index.map(titles)


# %%
reading["end"] = (reading.start + pd.to_timedelta(reading.duration, unit="h")).dt.round(
    "1s"
)
kindle["end"] = (kindle.start + pd.to_timedelta(kindle.duration, unit="h")).dt.round(
    "1s"
)


# %%
reading["match"] = 0
kindle["match"] = 0

match_id = 1
for date, subset in kindle.groupby("date"):
    for krow in subset.itertuples():
        for rrow in reading.loc[reading.date == date].itertuples():
            error = (
                abs(krow.start - rrow.start) + abs(krow.end - rrow.end)
            ).total_seconds()
            if error < 60 * 10:
                already_match = (
                    reading.loc[reading.start == rrow.start, "match"].iloc[0]
                    + kindle.loc[kindle.start == krow.start, "match"].iloc[0]
                )
                if already_match:
                    print(krow)
                    print(rrow)
                    print()
                reading.loc[reading.start == rrow.start, "match"] = match_id
                kindle.loc[kindle.start == krow.start, "match"] = match_id
                match_id += 1


# %%
%%capture cap --no-stderr
for row in df.loc[df.asum > 0].itertuples():
    print("\n\n-----------------------------------------------------------------------")
    print(
        f"rsum: {row.rsum:.4f}, asum: {row.asum:.4f}, ksum: {row.ksum:.4f}, err: {row.err:.4f}"
    )
    if row.err < 0.2 and row.ksum == 0:
        print(f"No kindle, low error, assume all audio")


    date = row[0]
    reading_events = reading.loc[reading.date == date]
    audible_events = audible.loc[audible.date == date]
    kindle_events = kindle.loc[kindle.date == date]

    for e in kindle_events.itertuples():
        print(f"kindle   {e.start}  {e.duration:.4f}  {e.match or ''}  {e.title}")
    print()
    for e in audible_events.itertuples():
        print(
            f"audible  {e.date.strftime("%Y-%m-%d")}                 {e.duration:.4f}  {e.title}"
        )
    print()
    for e in reading_events.itertuples():
        print(f"reading  {e.start}  {e.duration:.4f}  {e.match or ''}")
    print()

# %%
with open("output.txt", "w") as f:
    f.write(cap.stdout)


# %%
audio_times = [str(pd.to_datetime(line.strip(), utc=True).tz_convert("Europe/London")) for line in open("audio_times.txt").readlines()]


# %%
filepath = expandvars("$DIARY_DIR/data/atracker.tsv")
aevents = pd.read_table(filepath)

aevents.loc[aevents.start.isin(audio_times) & (aevents.category == "reading"), "category"] = "audiobook"

aevents.to_csv(filepath, sep="\t", index=False, float_format="%.4f")
