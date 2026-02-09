import json
import logging
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from .const import HEADERS, RAPIDAPI_KEY
from .db import get_db, init_ai_picks
from .utils.sport_config import SportConfig

logger = logging.getLogger(__name__)

# --- Timezone Configuration ---
LOCAL_TZ_NAME = 'America/Los_Angeles'  # PST/PDT


def _safe_parse_datetime(date_str: str):
    """Safely parse ISO datetime to UTC datetime, return None if invalid."""
    if not date_str or str(date_str).strip().lower() in ("none", "<none>", "null", "", "nan"):
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def utc_to_local_display(utc_dt, format_str='%a, %b %d, %I:%M %p %Z'):
    """
    Convert UTC datetime to local timezone (PST/PDT) for display.

    Args:
        utc_dt: datetime object in UTC or ISO string
        format_str: strftime format string

    Returns:
        Formatted string in local timezone
    """
    if not utc_dt:
        return ""

    try:
        # Handle string input
        if isinstance(utc_dt, str):
            utc_dt = _safe_parse_datetime(utc_dt)
            if not utc_dt:
                return ""

        # Ensure timezone aware
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=UTC)

        # Convert to local timezone
        local_tz = ZoneInfo(LOCAL_TZ_NAME)
        local_dt = utc_dt.astimezone(local_tz)

        return local_dt.strftime(format_str)
    except Exception:
        return str(utc_dt)

# -------------------------
# DB Migration for historical_games
# -------------------------


def migrate_historical_games():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS historical_games (
                id TEXT PRIMARY KEY,
                sport TEXT,
                game TEXT,
                score TEXT,
                winner TEXT,
                date TEXT,
                home_team TEXT,
                away_team TEXT
            )
        """)
        cur.execute("PRAGMA table_info(historical_games)")
        cols = {row['name'] for row in cur.fetchall()}
        if "home_team" not in cols:
            cur.execute(
                "ALTER TABLE historical_games ADD COLUMN home_team TEXT")
        if "away_team" not in cols:
            cur.execute(
                "ALTER TABLE historical_games ADD COLUMN away_team TEXT")
        conn.commit()


init_ai_picks()
migrate_historical_games()

# -------------------------
# Odds & Scores APIs
# -------------------------


def fetch_odds(sport="americanfootball_ncaaf"):
    """
    Fetch odds from RapidAPI with seasonal awareness and time-based filtering.

    Args:
        sport: Sport key (e.g., 'americanfootball_nfl')

    Returns:
        List of upcoming games with odds (next 3-7 days depending on sport)
    """
    # Check if sport is in season
    if not SportConfig.is_in_season(sport):
        logger.info(f"Odds API: Skipping {sport.upper()} - out of season")
        return []

    url = f"https://odds.p.rapidapi.com/v4/sports/{sport}/odds"
    querystring = {
        "regions": "us", "oddsFormat": "american",
        "markets": "h2h,spreads,totals", "dateFormat": "iso"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "odds.p.rapidapi.com"
    }

    try:
        r = requests.get(url, headers=headers, params=querystring, timeout=15)
        r.raise_for_status()
        all_games = r.json()
    except requests.exceptions.Timeout:
        logger.error(f"Odds API timeout for {sport}")
        return []
    except requests.exceptions.HTTPError as e:
        logger.error(
            f"Odds API HTTP error for {sport}: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"Odds API error for {sport}: {e}")
        return []

    now_utc = datetime.now(UTC)
    # UFC/MMA events are less frequent, so look 7 days ahead
    # Other sports look 3 days ahead
    days_ahead = 7 if sport == "mma_mixed_martial_arts" else 3
    max_future_date = now_utc + timedelta(days=days_ahead)
    future_games = []

    for game in all_games:
        dt = _safe_parse_datetime(game.get('commence_time'))
        if dt and now_utc < dt <= max_future_date:  # Filter to appropriate window
            game['commence_time'] = dt.isoformat()
            future_games.append(game)

    logger.info(
        f"Odds API: Found {len(future_games)}/{len(all_games)} upcoming games for {SportConfig.get_sport_name(sport)}")
    return future_games


def fetch_scores(sport="americanfootball_ncaaf", days_from=1):
    url = f"https://odds.p.rapidapi.com/v4/sports/{sport}/scores"
    params = {"daysFrom": days_from}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        logger.warning(
            f"Timeout fetching scores for {sport} (days_from={days_from})")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching scores for {sport}: {e}")
        return []
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON response for {sport} scores: {e}")
        return []

# -------------------------
# Historical Data Caching
# -------------------------


def _fetch_and_cache_historical_scores(sport_key, sport_name, team, limit=6, days_from=20):
    with get_db() as conn:
        cur = conn.cursor()
        history = []
        query = "SELECT * FROM historical_games WHERE sport = ? AND (home_team = ? OR away_team = ?) ORDER BY date DESC LIMIT ?"
        cur.execute(query, (sport_name, team, team, limit))
        cached_games = [dict(row) for row in cur.fetchall()]

        if len(cached_games) >= limit:
            return cached_games

        try:
            scores_data = fetch_scores(sport=sport_key, days_from=days_from)
        except Exception:
            return []

        for game in scores_data:
            if not game.get('completed', False):
                continue
            dt = _safe_parse_datetime(game.get('commence_time'))
            if not dt:
                continue
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            home_score = next((s['score'] for s in game.get(
                'scores', []) if s['name'] == home_team), '0')
            away_score = next((s['score'] for s in game.get(
                'scores', []) if s['name'] == away_team), '0')
            if not home_score or not away_score:
                continue

            record = {
                "id": game.get('id'),
                "sport": sport_name,
                "game": f"{away_team} @ {home_team}",
                "score": f"{home_score}-{away_score}",
                "winner": home_team if int(home_score) > int(away_score) else away_team,
                "date": dt.isoformat(),
                "home_team": home_team,
                "away_team": away_team,
            }
            cur.execute("""
                INSERT OR IGNORE INTO historical_games (id, sport, game, score, winner, date, home_team, away_team)
                VALUES (:id, :sport, :game, :score, :winner, :date, :home_team, :away_team)
            """, record)
            if team in (home_team, away_team):
                history.append(record)

        conn.commit()
    return sorted(history, key=lambda x: x['date'], reverse=True)[:limit]


def fetch_historical_ncaaf(team_name, limit=None):
    """Fetch NCAAF historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("americanfootball_ncaaf")
    days = SportConfig.get_historical_days("americanfootball_ncaaf")
    return _fetch_and_cache_historical_scores("americanfootball_ncaaf", "NCAAF", team_name, limit, days)


def fetch_historical_nfl(team_name, limit=None):
    """Fetch NFL historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("americanfootball_nfl")
    days = SportConfig.get_historical_days("americanfootball_nfl")
    return _fetch_and_cache_historical_scores("americanfootball_nfl", "NFL", team_name, limit, days)


def fetch_historical_mlb(team_name, limit=None):
    """Fetch MLB historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("baseball_mlb")
    days = SportConfig.get_historical_days("baseball_mlb")
    return _fetch_and_cache_historical_scores("baseball_mlb", "MLB", team_name, limit, days)


def fetch_historical_ncaab(team_name, limit=None):
    """Fetch NCAAB historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("basketball_ncaab")
    days = SportConfig.get_historical_days("basketball_ncaab")
    return _fetch_and_cache_historical_scores("basketball_ncaab", "NCAAB", team_name, limit, days)


def fetch_historical_nba(team_name, limit=None):
    """Fetch NBA historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("basketball_nba")
    days = SportConfig.get_historical_days("basketball_nba")
    return _fetch_and_cache_historical_scores("basketball_nba", "NBA", team_name, limit, days)


def fetch_historical_nhl(team_name, limit=None):
    """Fetch NHL historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("icehockey_nhl")
    days = SportConfig.get_historical_days("icehockey_nhl")
    return _fetch_and_cache_historical_scores("icehockey_nhl", "NHL", team_name, limit, days)


def fetch_historical_ufc(fighter_name, limit=None):
    """Fetch UFC historical fights with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("mma_mixed_martial_arts")
    days = SportConfig.get_historical_days("mma_mixed_martial_arts")
    return _fetch_and_cache_historical_scores("mma_mixed_martial_arts", "UFC", fighter_name, limit, days)


def fetch_historical_other(team_name, limit=10):
    return []


# -------------------------
# Re-exports for backward compatibility
# -------------------------
# These functions have been extracted to focused modules but are
# re-exported here so existing callers don't need to change imports.
from .grading import _check_pick_result, update_ai_pick_results  # noqa: F401,E402
from .llm import _call_claude_model, _call_gemini_model, _call_openai_model  # noqa: F401,E402
from .picks import generate_ai_picks  # noqa: F401,E402
