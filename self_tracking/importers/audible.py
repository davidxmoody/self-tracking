from self_tracking.dirs import diary_dir
import zipfile
import pandas as pd


zip_path = diary_dir / "data/exports/audible.zip"

with zipfile.ZipFile(zip_path, "r") as zf:
    with zf.open("Audible.Listening/Account Holder/Listening.csv") as file:
        df = pd.read_csv(file)

df = df.dropna()

df = pd.DataFrame(
    {
        "date": pd.to_datetime(df["Start Date"]),
        "duration": df["Event Duration Milliseconds"] / (1000 * 60 * 60),
        "title": df["Product Name"]
        .str.replace(r"\(.*?\)", "", regex=True)
        .str.replace(r"^(?!Ep)([^:]+):.*", r"\1", regex=True)
        .str.strip()
        .str.replace(r", Book \d$", "", regex=True),
    }
)

df = df.groupby(["date", "title"]).sum().reset_index()

df = df.loc[df.duration > (1 / 60)]

df.to_csv(
    diary_dir / "data/audible.tsv",
    sep="\t",
    index=False,
    float_format="%.4f",
)
