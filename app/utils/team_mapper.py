"""
Team name normalization utility for matching teams across different data sources.
Handles abbreviations, city names, full names, and common variations.
Also provides team ranking data from CSV files.
"""

import csv
import os
from typing import Optional, Dict, Tuple

# NFL Team Mappings
NFL_TEAMS = {
    # Arizona Cardinals
    "arizona": "Arizona Cardinals", "cardinals": "Arizona Cardinals", "ari": "Arizona Cardinals", "az": "Arizona Cardinals",

    # Atlanta Falcons
    "atlanta": "Atlanta Falcons", "falcons": "Atlanta Falcons", "atl": "Atlanta Falcons",

    # Baltimore Ravens
    "baltimore": "Baltimore Ravens", "ravens": "Baltimore Ravens", "bal": "Baltimore Ravens",

    # Buffalo Bills
    "buffalo": "Buffalo Bills", "bills": "Buffalo Bills", "buf": "Buffalo Bills",

    # Carolina Panthers
    "carolina": "Carolina Panthers", "panthers": "Carolina Panthers", "car": "Carolina Panthers",

    # Chicago Bears
    "chicago": "Chicago Bears", "bears": "Chicago Bears", "chi": "Chicago Bears",

    # Cincinnati Bengals
    "cincinnati": "Cincinnati Bengals", "bengals": "Cincinnati Bengals", "cin": "Cincinnati Bengals",

    # Cleveland Browns
    "cleveland": "Cleveland Browns", "browns": "Cleveland Browns", "cle": "Cleveland Browns",

    # Dallas Cowboys
    "dallas": "Dallas Cowboys", "cowboys": "Dallas Cowboys", "dal": "Dallas Cowboys",

    # Denver Broncos
    "denver": "Denver Broncos", "broncos": "Denver Broncos", "den": "Denver Broncos",

    # Detroit Lions
    "detroit": "Detroit Lions", "lions": "Detroit Lions", "det": "Detroit Lions",

    # Green Bay Packers
    "green bay": "Green Bay Packers", "packers": "Green Bay Packers", "gb": "Green Bay Packers",

    # Houston Texans
    "houston": "Houston Texans", "texans": "Houston Texans", "hou": "Houston Texans",

    # Indianapolis Colts
    "indianapolis": "Indianapolis Colts", "colts": "Indianapolis Colts", "ind": "Indianapolis Colts",

    # Jacksonville Jaguars
    "jacksonville": "Jacksonville Jaguars", "jaguars": "Jacksonville Jaguars", "jax": "Jacksonville Jaguars",

    # Kansas City Chiefs
    "kansas city": "Kansas City Chiefs", "chiefs": "Kansas City Chiefs", "kc": "Kansas City Chiefs",

    # Las Vegas Raiders
    "las vegas": "Las Vegas Raiders", "raiders": "Las Vegas Raiders", "lv": "Las Vegas Raiders", "oak": "Las Vegas Raiders",

    # Los Angeles Chargers
    "la chargers": "Los Angeles Chargers", "chargers": "Los Angeles Chargers", "lac": "Los Angeles Chargers",

    # Los Angeles Rams
    "la rams": "Los Angeles Rams", "rams": "Los Angeles Rams", "lar": "Los Angeles Rams",

    # Miami Dolphins
    "miami": "Miami Dolphins", "dolphins": "Miami Dolphins", "mia": "Miami Dolphins",

    # Minnesota Vikings
    "minnesota": "Minnesota Vikings", "vikings": "Minnesota Vikings", "min": "Minnesota Vikings",

    # New England Patriots
    "new england": "New England Patriots", "patriots": "New England Patriots", "ne": "New England Patriots",

    # New Orleans Saints
    "new orleans": "New Orleans Saints", "saints": "New Orleans Saints", "no": "New Orleans Saints",

    # New York Giants
    "ny giants": "New York Giants", "giants": "New York Giants", "nyg": "New York Giants",

    # New York Jets
    "ny jets": "New York Jets", "jets": "New York Jets", "nyj": "New York Jets",

    # Philadelphia Eagles
    "philadelphia": "Philadelphia Eagles", "eagles": "Philadelphia Eagles", "phi": "Philadelphia Eagles",

    # Pittsburgh Steelers
    "pittsburgh": "Pittsburgh Steelers", "steelers": "Pittsburgh Steelers", "pit": "Pittsburgh Steelers",

    # San Francisco 49ers
    "san francisco": "San Francisco 49ers", "49ers": "San Francisco 49ers", "sf": "San Francisco 49ers",

    # Seattle Seahawks
    "seattle": "Seattle Seahawks", "seahawks": "Seattle Seahawks", "sea": "Seattle Seahawks",

    # Tampa Bay Buccaneers
    "tampa bay": "Tampa Bay Buccaneers", "buccaneers": "Tampa Bay Buccaneers", "tb": "Tampa Bay Buccaneers", "bucs": "Tampa Bay Buccaneers",

    # Tennessee Titans
    "tennessee": "Tennessee Titans", "titans": "Tennessee Titans", "ten": "Tennessee Titans",

    # Washington Commanders
    "washington": "Washington Commanders", "commanders": "Washington Commanders", "was": "Washington Commanders", "wsh": "Washington Commanders",
}

# NBA Team Mappings
NBA_TEAMS = {
    # Atlanta Hawks
    "atlanta": "Atlanta Hawks", "hawks": "Atlanta Hawks", "atl": "Atlanta Hawks",

    # Boston Celtics
    "boston": "Boston Celtics", "celtics": "Boston Celtics", "bos": "Boston Celtics",

    # Brooklyn Nets
    "brooklyn": "Brooklyn Nets", "nets": "Brooklyn Nets", "bkn": "Brooklyn Nets",

    # Charlotte Hornets
    "charlotte": "Charlotte Hornets", "hornets": "Charlotte Hornets", "cha": "Charlotte Hornets",

    # Chicago Bulls
    "chicago": "Chicago Bulls", "bulls": "Chicago Bulls", "chi": "Chicago Bulls",

    # Cleveland Cavaliers
    "cleveland": "Cleveland Cavaliers", "cavaliers": "Cleveland Cavaliers", "cle": "Cleveland Cavaliers", "cavs": "Cleveland Cavaliers",

    # Dallas Mavericks
    "dallas": "Dallas Mavericks", "mavericks": "Dallas Mavericks", "dal": "Dallas Mavericks", "mavs": "Dallas Mavericks",

    # Denver Nuggets
    "denver": "Denver Nuggets", "nuggets": "Denver Nuggets", "den": "Denver Nuggets",

    # Detroit Pistons
    "detroit": "Detroit Pistons", "pistons": "Detroit Pistons", "det": "Detroit Pistons",

    # Golden State Warriors
    "golden state": "Golden State Warriors", "warriors": "Golden State Warriors", "gs": "Golden State Warriors", "gsw": "Golden State Warriors",

    # Houston Rockets
    "houston": "Houston Rockets", "rockets": "Houston Rockets", "hou": "Houston Rockets",

    # Indiana Pacers
    "indiana": "Indiana Pacers", "pacers": "Indiana Pacers", "ind": "Indiana Pacers",

    # LA Clippers
    "la clippers": "LA Clippers", "clippers": "LA Clippers", "lac": "LA Clippers",

    # LA Lakers / Los Angeles Lakers
    "la lakers": "LA Lakers", "lakers": "LA Lakers", "lal": "LA Lakers", "los angeles lakers": "LA Lakers", "l.a. lakers": "LA Lakers",

    # Memphis Grizzlies
    "memphis": "Memphis Grizzlies", "grizzlies": "Memphis Grizzlies", "mem": "Memphis Grizzlies",

    # Miami Heat
    "miami": "Miami Heat", "heat": "Miami Heat", "mia": "Miami Heat",

    # Milwaukee Bucks
    "milwaukee": "Milwaukee Bucks", "bucks": "Milwaukee Bucks", "mil": "Milwaukee Bucks",

    # Minnesota Timberwolves
    "minnesota": "Minnesota Timberwolves", "timberwolves": "Minnesota Timberwolves", "min": "Minnesota Timberwolves", "twolves": "Minnesota Timberwolves",

    # New Orleans Pelicans
    "new orleans": "New Orleans Pelicans", "pelicans": "New Orleans Pelicans", "no": "New Orleans Pelicans", "nop": "New Orleans Pelicans",

    # New York Knicks
    "new york": "New York Knicks", "knicks": "New York Knicks", "ny": "New York Knicks", "nyk": "New York Knicks",

    # Oklahoma City Thunder
    "oklahoma city": "Oklahoma City Thunder", "thunder": "Oklahoma City Thunder", "okc": "Oklahoma City Thunder",

    # Orlando Magic
    "orlando": "Orlando Magic", "magic": "Orlando Magic", "orl": "Orlando Magic",

    # Philadelphia 76ers
    "philadelphia": "Philadelphia 76ers", "76ers": "Philadelphia 76ers", "phi": "Philadelphia 76ers", "sixers": "Philadelphia 76ers",

    # Phoenix Suns
    "phoenix": "Phoenix Suns", "suns": "Phoenix Suns", "phx": "Phoenix Suns",

    # Portland Trail Blazers
    "portland": "Portland Trail Blazers", "trail blazers": "Portland Trail Blazers", "por": "Portland Trail Blazers", "blazers": "Portland Trail Blazers",

    # Sacramento Kings
    "sacramento": "Sacramento Kings", "kings": "Sacramento Kings", "sac": "Sacramento Kings",

    # San Antonio Spurs
    "san antonio": "San Antonio Spurs", "spurs": "San Antonio Spurs", "sa": "San Antonio Spurs", "sas": "San Antonio Spurs",

    # Toronto Raptors
    "toronto": "Toronto Raptors", "raptors": "Toronto Raptors", "tor": "Toronto Raptors",

    # Utah Jazz
    "utah": "Utah Jazz", "jazz": "Utah Jazz", "uta": "Utah Jazz",

    # Washington Wizards
    "washington": "Washington Wizards", "wizards": "Washington Wizards", "was": "Washington Wizards", "wsh": "Washington Wizards",
}


def normalize_team_name(team_input: str, sport: str = None) -> str:
    """
    Normalize team name to canonical form.

    Args:
        team_input: Raw team name (e.g., "OKC", "Oklahoma City", "Thunder")
        sport: Sport context ("NFL", "NBA", "NCAAB", "NCAAF") - helps with disambiguation

    Returns:
        Normalized team name or original if no match found
    """
    if not team_input:
        return team_input

    # Clean input
    clean_input = team_input.strip().lower()
    clean_input = clean_input.replace(".", "").replace("-", " ")

    # Try exact match first
    if sport in ["NFL", "americanfootball_nfl"]:
        if clean_input in NFL_TEAMS:
            return NFL_TEAMS[clean_input]
        # Try full name match
        for key, value in NFL_TEAMS.items():
            if value.lower() == clean_input:
                return value

    elif sport in ["NBA", "basketball_nba"]:
        if clean_input in NBA_TEAMS:
            return NBA_TEAMS[clean_input]
        # Try full name match
        for key, value in NBA_TEAMS.items():
            if value.lower() == clean_input:
                return value

    # If no sport specified, try both
    if clean_input in NFL_TEAMS:
        return NFL_TEAMS[clean_input]
    if clean_input in NBA_TEAMS:
        return NBA_TEAMS[clean_input]

    # Return original if no match
    return team_input


def match_teams(team1: str, team2: str, sport: str = None) -> bool:
    """
    Check if two team names refer to the same team.

    Args:
        team1: First team name
        team2: Second team name
        sport: Sport context for disambiguation

    Returns:
        True if teams match, False otherwise
    """
    norm1 = normalize_team_name(team1, sport)
    norm2 = normalize_team_name(team2, sport)
    return norm1.lower() == norm2.lower()


def extract_team_from_game_title(game_title: str, sport: str = None) -> tuple:
    """
    Extract both teams from a game title like "Team A @ Team B" or "Team A vs Team B".

    Returns:
        (away_team, home_team) tuple
    """
    if "@" in game_title:
        parts = game_title.split("@")
    elif " vs " in game_title.lower():
        parts = game_title.lower().split(" vs ")
    elif " v " in game_title.lower():
        parts = game_title.lower().split(" v ")
    else:
        return (None, None)

    if len(parts) != 2:
        return (None, None)

    away = normalize_team_name(parts[0].strip(), sport)
    home = normalize_team_name(parts[1].strip(), sport)

    return (away, home)


# ============================================================================
# TEAM RANKING DATA
# ============================================================================

# Cache for ranking data
_NCAAB_RANKINGS_CACHE = None
_NCAAF_RANKINGS_CACHE = None


def _load_ncaab_rankings() -> Dict[str, Dict]:
    """Load NCAAB rankings from CSV file."""
    global _NCAAB_RANKINGS_CACHE

    if _NCAAB_RANKINGS_CACHE is not None:
        return _NCAAB_RANKINGS_CACHE

    rankings = {}
    csv_path = os.path.join(os.path.dirname(__file__),
                            '../../data/ncaab_teams.csv')

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_name = row['Team'].strip()
                normalized_name = normalize_team_name(team_name, "NCAAB")

                if normalized_name:
                    rankings[normalized_name] = {
                        'rank': int(row['Rank']),
                        'ap_rank': row.get('AP_Rank', '').strip() or None,
                        'coaches_rank': row.get('Coaches_Rank', '').strip() or None,
                        'cbs_rank': row.get('CBS_Rank', '').strip() or None,
                        'date': row.get('Date', '').strip()
                    }

        _NCAAB_RANKINGS_CACHE = rankings
        print(f"✅ Loaded {len(rankings)} NCAAB team rankings")
        return rankings

    except FileNotFoundError:
        print(f"⚠️ NCAAB rankings file not found: {csv_path}")
        _NCAAB_RANKINGS_CACHE = {}
        return {}
    except Exception as e:
        print(f"❌ Error loading NCAAB rankings: {e}")
        _NCAAB_RANKINGS_CACHE = {}
        return {}


def _load_ncaaf_rankings() -> Dict[str, Dict]:
    """Load NCAAF rankings from CSV file."""
    global _NCAAF_RANKINGS_CACHE

    if _NCAAF_RANKINGS_CACHE is not None:
        return _NCAAF_RANKINGS_CACHE

    rankings = {}
    csv_path = os.path.join(os.path.dirname(__file__),
                            '../../data/ncaaf_teams.csv')

    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                team_name = row['Team'].strip()
                normalized_name = normalize_team_name(team_name, "NCAAF")

                if normalized_name:
                    rankings[normalized_name] = {
                        'rank': int(row['Rank']),
                        'source': row.get('Source', '').strip(),
                        'conference': row.get('Conference', '').strip(),
                        'date': row.get('Date', '').strip()
                    }

        _NCAAF_RANKINGS_CACHE = rankings
        print(f"✅ Loaded {len(rankings)} NCAAF team rankings")
        return rankings

    except FileNotFoundError:
        print(f"⚠️ NCAAF rankings file not found: {csv_path}")
        _NCAAF_RANKINGS_CACHE = {}
        return {}
    except Exception as e:
        print(f"❌ Error loading NCAAF rankings: {e}")
        _NCAAF_RANKINGS_CACHE = {}
        return {}


def get_team_rank(team_name: str, sport: str) -> Optional[int]:
    """
    Get the ranking for a team.

    Args:
        team_name: Team name (will be normalized)
        sport: Sport key (e.g., 'NCAAB', 'basketball_ncaab', 'NCAAF', 'americanfootball_ncaaf')

    Returns:
        Team rank (1-50) or None if not ranked
    """
    normalized_name = normalize_team_name(team_name, sport)
    if not normalized_name:
        return None

    sport_upper = sport.upper()

    if "NCAAB" in sport_upper or "BASKETBALL_NCAAB" in sport_upper:
        rankings = _load_ncaab_rankings()
        team_data = rankings.get(normalized_name)
        return team_data['rank'] if team_data else None

    elif "NCAAF" in sport_upper or "AMERICANFOOTBALL_NCAAF" in sport_upper:
        rankings = _load_ncaaf_rankings()
        team_data = rankings.get(normalized_name)
        return team_data['rank'] if team_data else None

    return None


def get_team_ranking_info(team_name: str, sport: str) -> Optional[Dict]:
    """
    Get full ranking information for a team.

    Args:
        team_name: Team name (will be normalized)
        sport: Sport key (e.g., 'NCAAB', 'basketball_ncaab', 'NCAAF', 'americanfootball_ncaaf')

    Returns:
        Dictionary with ranking info or None if not ranked
    """
    normalized_name = normalize_team_name(team_name, sport)
    if not normalized_name:
        return None

    sport_upper = sport.upper()

    if "NCAAB" in sport_upper or "BASKETBALL_NCAAB" in sport_upper:
        rankings = _load_ncaab_rankings()
        return rankings.get(normalized_name)

    elif "NCAAF" in sport_upper or "AMERICANFOOTBALL_NCAAF" in sport_upper:
        rankings = _load_ncaaf_rankings()
        return rankings.get(normalized_name)

    return None


def get_matchup_quality(away_team: str, home_team: str, sport: str) -> Dict:
    """
    Analyze matchup quality based on team rankings.

    Args:
        away_team: Away team name
        home_team: Home team name
        sport: Sport key

    Returns:
        Dictionary with matchup analysis
    """
    away_rank = get_team_rank(away_team, sport)
    home_rank = get_team_rank(home_team, sport)

    result = {
        'away_team': away_team,
        'home_team': home_team,
        'away_rank': away_rank,
        'home_rank': home_rank,
        'matchup_type': 'unranked',
        'quality_score': 0
    }

    # Determine matchup type
    if away_rank and home_rank:
        result['matchup_type'] = 'ranked_vs_ranked'

        # Top 10 vs Top 10
        if away_rank <= 10 and home_rank <= 10:
            result['matchup_type'] = 'top10_vs_top10'
            result['quality_score'] = 10
        # Top 25 vs Top 25
        elif away_rank <= 25 and home_rank <= 25:
            result['matchup_type'] = 'top25_vs_top25'
            result['quality_score'] = 8
        # Ranked vs Ranked
        else:
            result['quality_score'] = 6

        # Add rank differential
        result['rank_differential'] = abs(away_rank - home_rank)

    elif away_rank or home_rank:
        result['matchup_type'] = 'ranked_vs_unranked'
        result['quality_score'] = 4

        if away_rank and away_rank <= 10:
            result['matchup_type'] = 'top10_vs_unranked'
            result['quality_score'] = 5
        elif home_rank and home_rank <= 10:
            result['matchup_type'] = 'top10_vs_unranked'
            result['quality_score'] = 5

    return result


def enrich_game_with_rankings(game_title: str, sport: str) -> Dict:
    """
    Enrich a game with ranking information.

    Args:
        game_title: Game title (e.g., "Duke Blue Devils @ UConn Huskies")
        sport: Sport key

    Returns:
        Dictionary with game info and rankings
    """
    away_team, home_team = extract_team_from_game_title(game_title, sport)

    if not away_team or not home_team:
        return {
            'game_title': game_title,
            'error': 'Could not parse teams from game title'
        }

    matchup = get_matchup_quality(away_team, home_team, sport)

    away_info = get_team_ranking_info(away_team, sport)
    home_info = get_team_ranking_info(home_team, sport)

    return {
        'game_title': game_title,
        'away_team': away_team,
        'home_team': home_team,
        'away_ranking': away_info,
        'home_ranking': home_info,
        'matchup_quality': matchup
    }
