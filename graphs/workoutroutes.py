# %% Imports

from glob import glob
from os.path import expandvars

from gpxplotter import add_segment_to_map, create_folium_map, read_gpx_file


# %% Load

segments = []
for f in glob(expandvars("$HOME/Downloads/export/*.gpx")):
    segments.extend(next(read_gpx_file(f))["segments"])


# %% Graphs

line_options = {"color": "red", "weight": 5, "opacity": 0.6}

map = create_folium_map()

for segment in segments:
    add_segment_to_map(map, segment, line_options=line_options)

map.show_in_browser()
