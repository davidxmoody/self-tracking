import re
import gzip
from os.path import expandvars
from zipfile import ZipFile

pattern = r"^export/(\d{4}-\d{2}-\d{2}) (\d{2}-\d{2}-\d{2}) (\w+).gpx$"

infilepath = expandvars("$HOME/Downloads/workout-routes/Export.zip")

with ZipFile(infilepath) as infile:
    for route in infile.namelist():
        match = re.match(pattern, route)
        if not match:
            raise Exception(f"Could not parse route file name: '{route}'")

        date = match.group(1)
        time = match.group(2)
        activity = match.group(3).lower()

        outfilepath = expandvars(
            f"$DIARY_DIR/data/routes/{date}_{time}_{activity}.gpx.gz"
        )

        with gzip.open(outfilepath, "wb") as outfile:
            outfile.write(infile.read(route))
