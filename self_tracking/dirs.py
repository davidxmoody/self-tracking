from pathlib import Path
from os.path import expandvars

cache_dir = Path(expandvars("$HOME/.cache"))
diary_dir = Path(expandvars("$DIARY_DIR"))
downloads_dir = Path(expandvars("$HOME/Downloads"))
git_backup_dir = Path(expandvars("$GIT_BACKUP_DIR"))
icloud_dir = Path(expandvars("$ICLOUD_DIR"))
projects_dir = Path(expandvars("$P_DIR"))
