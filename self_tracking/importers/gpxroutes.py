import gzip
from os.path import basename, expandvars
from zipfile import ZipFile


def main():
    with ZipFile(expandvars("$HOME/Downloads/Export.zip")) as zipfile:
        for route in zipfile.namelist():
            filename = basename(route).replace(" ", "_").lower() + ".gz"
            filepath = expandvars(f"$DIARY_DIR/data/routes/{filename}")
            with gzip.open(filepath, "wb") as file:
                file.write(zipfile.read(route))


if __name__ == "__main__":
    main()
