"""Estimate time spent per project by combining tracked project sessions with git commits.

Each tracked "project" session is allocated to repos in tiers:

1. Commits inside the session (with a little slack either side): the session is
   split between repos by the time leading up to each commit ("gap" method), so a
   repo that was being worked on for 40 minutes before its commit gets ~40 minutes.
2. No commits in the session: the work was probably committed later (or was a
   continuation of earlier work), so the session is split between repos with
   commits shortly *after* it (strongly weighted) or shortly *before* it, using
   exponential time decay ("neighbours" method).
3. Nothing nearby: the session is labelled "unknown" so totals stay honest.

Dotfiles get special handling: on days with only a few dotfiles commits they are
treated as one-off tweaks that are credited a small fixed amount of time and don't
count as evidence of what the rest of the session was spent on. On days with
several dotfiles commits it's treated as a normal project.
"""

# %%
import numpy as np
import pandas as pd

import self_tracking.data as d

project_events = d.atracker_events().query("category == 'project'")

commits = d.git_commits()

# %% Tunable parameters
SESSION_PRE = pd.Timedelta(minutes=15)  # commits just before a timer started still count
SESSION_POST = pd.Timedelta(minutes=30)  # commits just after a timer stopped still count

DOTFILES_REPO = "dotfiles"
DOTFILES_ACTIVE_MIN_COMMITS = 3  # dotfiles commits in a day to count as real dotfiles work
MINOR_COMMIT_HOURS = 0.1  # time credited per one-off dotfiles tweak

FORWARD_WINDOW = pd.Timedelta(days=7)  # look this far ahead for uncommitted work
FORWARD_TAU = pd.Timedelta(days=2)
BACKWARD_WINDOW = pd.Timedelta(days=3)  # ...and this far back
BACKWARD_TAU = pd.Timedelta(days=1)
MIN_INFERRED_SHARE = 0.1  # drop inferred repo shares smaller than this

UNKNOWN = "unknown"
DAY_OFFSET = pd.Timedelta(hours=6)  # same "day starts at 6am" convention as atracker_events


# %% Prepare data
def prepare_events(events: pd.DataFrame, commits: pd.DataFrame) -> pd.DataFrame:
    events = events.loc[events.start >= commits.datetime.min(), ["start", "duration", "date"]]
    return (
        events.assign(end=events.start + pd.to_timedelta(events.duration, unit="h"))
        .sort_values("start")
        .reset_index(drop=True)
    )


def prepare_commits(commits: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    # Only keep commits that could act as evidence for some tracked session
    lo = events.start.min() - BACKWARD_WINDOW
    hi = events.end.max() + FORWARD_WINDOW
    commits = commits.loc[commits.datetime.between(lo, hi)].copy()
    commits["date"] = pd.to_datetime((commits.datetime - DAY_OFFSET).dt.date)

    is_dotfiles = commits.repo == DOTFILES_REPO
    dotfiles_per_day = commits.loc[is_dotfiles].groupby("date").size()
    commits["minor"] = is_dotfiles & (
        commits.date.map(dotfiles_per_day).fillna(0) < DOTFILES_ACTIVE_MIN_COMMITS
    )
    return commits.sort_values("datetime").reset_index(drop=True)


# %% Allocation methods
def split_by_gaps(start: pd.Timestamp, end: pd.Timestamp, session_commits: pd.DataFrame):
    """Credit each commit's repo with the time since the previous commit (or session start).
    Time after the last commit goes to the last commit's repo."""
    times = session_commits.datetime.clip(start, end).tolist()
    repos = session_commits.repo.tolist()
    bounds = [start, *times]

    shares: dict[str, float] = {}
    for i, repo in enumerate(repos):
        shares[repo] = shares.get(repo, 0.0) + (times[i] - bounds[i]).total_seconds()
    shares[repos[-1]] += (end - times[-1]).total_seconds()

    total = sum(shares.values())
    if total == 0:  # zero-length session: fall back to commit counts
        counts = session_commits.repo.value_counts()
        return (counts / counts.sum()).to_dict()
    return {repo: s / total for repo, s in shares.items()}


def split_by_neighbours(start: pd.Timestamp, end: pd.Timestamp, major_commits: pd.DataFrame):
    """Weight repos by commits shortly after (preferred) or before the session."""
    after = (major_commits.datetime - end) / FORWARD_TAU
    before = (start - major_commits.datetime) / BACKWARD_TAU
    is_after = (major_commits.datetime > end) & (major_commits.datetime <= end + FORWARD_WINDOW)
    is_before = (major_commits.datetime < start) & (
        major_commits.datetime >= start - BACKWARD_WINDOW
    )
    # Clip before exp so out-of-window commits (masked to 0 anyway) can't overflow
    weights = pd.Series(
        np.where(
            is_after,
            np.exp(-after.clip(lower=0)),
            np.where(is_before, np.exp(-before.clip(lower=0)), 0.0),
        ),
        index=major_commits.index,
    )
    by_repo = weights.groupby(major_commits.repo).sum()
    by_repo = by_repo[by_repo > 0]
    if by_repo.empty:
        return {}

    shares = by_repo / by_repo.sum()
    shares = shares[shares >= MIN_INFERRED_SHARE]
    return (shares / shares.sum()).to_dict()


def allocate(events: pd.DataFrame, commits: pd.DataFrame) -> pd.DataFrame:
    major = commits.loc[~commits.minor]
    used_minor: set[int] = set()  # so a tweak near two sessions is only credited once
    rows = []

    def add(event, shares: dict[str, float], hours: float, method: str):
        for repo, share in shares.items():
            rows.append(
                {"date": event.date, "repo": repo, "duration": hours * share, "method": method}
            )

    for event in events.itertuples():
        in_session = commits.loc[
            commits.datetime.between(event.start - SESSION_PRE, event.end + SESSION_POST)
        ]
        session_major = in_session.loc[~in_session.minor]
        session_minor = in_session.loc[
            in_session.minor & ~in_session.index.isin(list(used_minor))
        ]
        used_minor.update(session_minor.index)

        remaining = event.duration

        # Small fixed credit for one-off dotfiles tweaks
        if not session_minor.empty:
            minor_hours = min(len(session_minor) * MINOR_COMMIT_HOURS, remaining)
            add(event, {DOTFILES_REPO: 1.0}, minor_hours, "minor")
            remaining -= minor_hours
        if remaining <= 0:
            continue

        if not session_major.empty:
            add(event, split_by_gaps(event.start, event.end, session_major), remaining, "gaps")
            continue

        shares = split_by_neighbours(event.start, event.end, major)
        if shares:
            add(event, shares, remaining, "neighbours")
        elif not session_minor.empty:
            # Only dotfiles tweaks and nothing else nearby: probably was dotfiles work
            add(event, {DOTFILES_REPO: 1.0}, remaining, "minor-fallback")
        else:
            add(event, {UNKNOWN: 1.0}, remaining, UNKNOWN)

    return pd.DataFrame(rows, columns=["date", "repo", "duration", "method"])


# %% Run
events = prepare_events(project_events, commits)
evidence = prepare_commits(commits, events)
allocations = allocate(events, evidence)

project_time = (
    allocations.groupby(["date", "repo"], as_index=False)
    .duration.sum()
    .sort_values(["date", "duration"], ascending=[True, False])
    .reset_index(drop=True)
)

# %% Summary
if __name__ == "__main__":
    pd.set_option("display.width", 200)
    print(project_time)
    print(f"\nTracked: {events.duration.sum():.1f}h, allocated: {project_time.duration.sum():.1f}h")
    print("\nHours by repo:")
    print(project_time.groupby("repo").duration.sum().sort_values(ascending=False).round(1))
    print("\nHours by method:")
    print(allocations.groupby("method").duration.sum().round(1))
