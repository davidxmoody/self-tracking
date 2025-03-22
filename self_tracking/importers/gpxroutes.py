import gzip
from os.path import expandvars
from pathlib import Path

import_dir = Path(
    expandvars("$HOME/Library/Mobile Documents/com~apple~CloudDocs/Health/Routes")
)

export_dir = Path(expandvars("$DIARY_DIR/data/routes"))


def main():
    skip_count = 0

    for import_file in import_dir.glob("*.gpx"):
        export_file = export_dir / (import_file.name.replace(" ", "_").lower() + ".gz")

        if export_file.exists():
            skip_count += 1
            continue

        print(f"Importing: {export_file.name}")
        with import_file.open("rb") as f_in, gzip.open(export_file, "wb") as f_out:
            f_out.writelines(f_in)

    print(f"Skipped {skip_count} existing routes")


if __name__ == "__main__":
    main()
