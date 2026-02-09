"""
Team name normalizer to ensure consistent game_id generation across all scrapers.
Maps various team name formats to canonical short names.
"""

# NBA Team Name Mappings
NBA_TEAM_NAMES = {
    # Atlanta Hawks
    "atlanta": "Atlanta",
    "atlanta hawks": "Atlanta",
    "hawks": "Atlanta",

    # Boston Celtics
    "boston": "Boston",
    "boston celtics": "Boston",
    "celtics": "Boston",

    # Brooklyn Nets
    "brooklyn": "Brooklyn",
    "brooklyn nets": "Brooklyn",
    "nets": "Brooklyn",

    # Charlotte Hornets
    "charlotte": "Charlotte",
    "charlotte hornets": "Charlotte",
    "hornets": "Charlotte",

    # Chicago Bulls
    "chicago": "Chicago",
    "chicago bulls": "Chicago",
    "bulls": "Chicago",

    # Cleveland Cavaliers
    "cleveland": "Cleveland",
    "cleveland cavaliers": "Cleveland",
    "cavaliers": "Cleveland",
    "cavs": "Cleveland",

    # Dallas Mavericks
    "dallas": "Dallas",
    "dallas mavericks": "Dallas",
    "mavericks": "Dallas",
    "mavs": "Dallas",

    # Denver Nuggets
    "denver": "Denver",
    "denver nuggets": "Denver",
    "nuggets": "Denver",

    # Detroit Pistons
    "detroit": "Detroit",
    "detroit pistons": "Detroit",
    "pistons": "Detroit",

    # Golden State Warriors
    "golden state": "GoldenState",
    "golden state warriors": "GoldenState",
    "warriors": "GoldenState",

    # Houston Rockets
    "houston": "Houston",
    "houston rockets": "Houston",
    "rockets": "Houston",

    # Indiana Pacers
    "indiana": "Indiana",
    "indiana pacers": "Indiana",
    "pacers": "Indiana",

    # LA Clippers
    "la clippers": "LAClippers",
    "los angeles clippers": "LAClippers",
    "clippers": "LAClippers",

    # LA Lakers
    "la lakers": "LALakers",
    "los angeles lakers": "LALakers",
    "lakers": "LALakers",

    # Memphis Grizzlies
    "memphis": "Memphis",
    "memphis grizzlies": "Memphis",
    "grizzlies": "Memphis",

    # Miami Heat
    "miami": "Miami",
    "miami heat": "Miami",
    "heat": "Miami",

    # Milwaukee Bucks
    "milwaukee": "Milwaukee",
    "milwaukee bucks": "Milwaukee",
    "bucks": "Milwaukee",

    # Minnesota Timberwolves
    "minnesota": "Minnesota",
    "minnesota timberwolves": "Minnesota",
    "timberwolves": "Minnesota",

    # New Orleans Pelicans
    "new orleans": "NewOrleans",
    "new orleans pelicans": "NewOrleans",
    "pelicans": "NewOrleans",

    # New York Knicks
    "new york": "NewYork",
    "new york knicks": "NewYork",
    "knicks": "NewYork",

    # Oklahoma City Thunder
    "oklahoma city": "OklahomaCity",
    "oklahoma city thunder": "OklahomaCity",
    "thunder": "OklahomaCity",

    # Orlando Magic
    "orlando": "Orlando",
    "orlando magic": "Orlando",
    "magic": "Orlando",

    # Philadelphia 76ers
    "philadelphia": "Philadelphia",
    "philadelphia 76ers": "Philadelphia",
    "76ers": "Philadelphia",
    "sixers": "Philadelphia",

    # Phoenix Suns
    "phoenix": "Phoenix",
    "phoenix suns": "Phoenix",
    "suns": "Phoenix",

    # Portland Trail Blazers
    "portland": "Portland",
    "portland trail blazers": "Portland",
    "trail blazers": "Portland",
    "blazers": "Portland",

    # Sacramento Kings
    "sacramento": "Sacramento",
    "sacramento kings": "Sacramento",
    "kings": "Sacramento",

    # San Antonio Spurs
    "san antonio": "SanAntonio",
    "san antonio spurs": "SanAntonio",
    "spurs": "SanAntonio",

    # Toronto Raptors
    "toronto": "Toronto",
    "toronto raptors": "Toronto",
    "raptors": "Toronto",

    # Utah Jazz
    "utah": "Utah",
    "utah jazz": "Utah",
    "jazz": "Utah",

    # Washington Wizards
    "washington": "Washington",
    "washington wizards": "Washington",
    "wizards": "Washington",
}


def normalize_team_name(team_name: str, sport: str = "NBA") -> str:
    """
    Normalize team name to canonical format for consistent game_id generation.

    Args:
        team_name: Raw team name from scraper (e.g., "Charlotte Hornets", "Charlotte", "Hornets")
        sport: Sport key (e.g., "NBA", "NFL", "NCAAB", "NCAAF")

    Returns:
        Canonical team name (e.g., "Charlotte")
    """
    # Clean up the input
    clean_name = team_name.strip().lower()

    # Select the appropriate mapping based on sport
    if sport.upper() == "NBA":
        mapping = NBA_TEAM_NAMES
    else:
        # For other sports, just return cleaned name for now
        # TODO: Add NFL, NCAAB, NCAAF mappings
        return team_name.replace(' ', '')

    # Look up in mapping
    if clean_name in mapping:
        return mapping[clean_name]

    # Fallback: return original with spaces removed
    return team_name.replace(' ', '')

