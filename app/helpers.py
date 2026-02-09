from pathlib import Path

import pandas as pd

# -------------------------
# Helpers for NFL team IDs
# -------------------------
NFL_TEAM_IDS = {}
NCAAF_TEAMS = []
MLB_TEAM_IDS = []


def load_nfl_team_ids():
    """Load NFL teams CSV into dict {displayName: id} and {slug: id}"""
    from pathlib import Path

    import pandas as pd

    path = Path(__file__).parent.parent / "data" / "nfl_teams.csv"
    if not path.exists():
        return {}

    # Auto-detect header row and skip bad ones
    df = pd.read_csv(path)

    lookup = {}
    for _, row in df.iterrows():
        try:
            lookup[row["name"]] = int(row["id"])
            lookup[row["slug"]] = int(row["id"])
        except (ValueError, KeyError):
            # skip rows like "Division,Team,Id" or malformed data
            continue
    return lookup


def load_ncaaf_teams():
    path = Path(__file__).parent.parent / "data" / "ncaaf_teams.csv"
    if path.exists():
        return pd.read_csv(path).to_dict(orient="records")
    return []


def load_mlb_team_ids():
    """Load MLB teams CSV into dict {displayName: id} and {slug: id}"""
    from pathlib import Path

    import pandas as pd

    path = Path(__file__).parent.parent / "data" / "mlb_teams.csv"
    if not path.exists():
        return {}

    df = pd.read_csv(path, header=None, names=["slug", "name", "id"])
    lookup = {}
    for _, row in df.iterrows():
        try:
            team_id = int(str(row["id"]).strip())
        except (ValueError, TypeError):
            # skip rows where id isn't an integer
            continue
        lookup[row["name"]] = team_id
        lookup[row["slug"]] = team_id
    return lookup


# Initialize at import
NFL_TEAM_IDS = load_nfl_team_ids()
NCAAF_TEAMS = load_ncaaf_teams()
MLB_TEAM_IDS = load_mlb_team_ids()
