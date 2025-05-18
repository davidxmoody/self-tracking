from pathlib import Path
from os.path import expandvars

cache_dir = Path(expandvars("$HOME/.cache"))
diary_dir = Path(expandvars("$DIARY_DIR"))
downloads_dir = Path(expandvars("$HOME/Downloads"))
icloud_dir = Path(expandvars("$ICLOUD_DIR"))
projects_dir = Path(expandvars("$P_DIR"))
