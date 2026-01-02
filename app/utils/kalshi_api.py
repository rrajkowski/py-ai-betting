from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
import requests
import re
from app.utils.db import insert_context
from app.utils.sport_config import SportConfig
from app.utils.team_mapper import normalize_team_name
from app.utils.scraper import create_game_id
from dotenv import load_dotenv

load_dotenv()


class KalshiClient:
    """
    Kalshi API client wrapper for public market data requests only (no auth).
    """

    # NOTE: Using the standard production API URL
    API_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self):
        self.session = requests.Session()

    def request(self, method: str, path: str, params: Optional[dict] = None) -> Optional[requests.Response]:
        """Perform an unauthenticated Kalshi API request (public market data)."""
        url = f"{self.API_URL}{path}"
        try:
            response = self.session.request(method, url, params=params)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            print(
                f"❌ Kalshi API failed (HTTP {e.response.status_code}): Path={path}. Error: {e}"
            )
        except requests.exceptions.RequestException as e:
            print(f"❌ Kalshi API failed (Connection Error): {e}")
        return None


def extract_game_date_from_ticker(ticker: str) -> Optional[str]:
    """
    Extract game date from Kalshi ticker.

    Format: KXNBAGAME-25DEC26BOSIND-BOS -> 2025-12-26

    Args:
        ticker: Kalshi market ticker

    Returns:
        Game date in YYYY-MM-DD format, or None if parsing fails
    """
    # Extract date from ticker (e.g., "25DEC26" -> 2025-12-26)
    match = re.search(r'(\d{2})([A-Z]{3})(\d{2})', ticker)
    if not match:
        return None

    year = f"20{match.group(1)}"
    month_str = match.group(2)
    day = match.group(3)

    # Convert month abbreviation to number
    months = {
        "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
        "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
        "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
    }
    month = months.get(month_str)
    if not month:
        return None

    return f"{year}-{month}-{day}"


def extract_teams_from_kalshi_ticker(ticker: str, sport_key: str) -> Optional[Tuple[str, str]]:
    """
    Extract team abbreviations from Kalshi ticker and normalize to full names.

    Format examples:
    - KXNBAGAME-25DEC26BOSIND-BOS -> ("Boston Celtics", "Indiana Pacers")
    - KXNBASPREAD-25DEC26LACPOR-POR7 -> ("LA Clippers", "Portland Trail Blazers")
    - KXNFLGAME-25DEC28PITKCW-PIT -> ("Pittsburgh Steelers", "Kansas City Chiefs")
    - KXNBAGAME-25DEC27BKNMIN-MIN -> ("Brooklyn Nets", "Minnesota Timberwolves")

    Args:
        ticker: Kalshi market ticker
        sport_key: Sport key (e.g., 'basketball_nba', 'americanfootball_nfl')

    Returns:
        Tuple of (away_team, home_team) in normalized full names, or None if parsing fails
    """
    # Extract team abbreviations from ticker
    # Pattern: KXSPORT-YYMMMDDteam1team2-team_or_line
    # Team abbreviations are typically 3 letters each, followed by optional numbers

    # First, extract the date and team portion (e.g., "25DEC26LACPOR")
    date_teams_match = re.search(r'-(\d{2}[A-Z]{3}\d{2}[A-Z]{6})-', ticker)
    if not date_teams_match:
        return None

    date_teams = date_teams_match.group(1)

    # Extract the 6-letter team portion (e.g., "LACPOR" from "25DEC26LACPOR")
    teams_match = re.search(r'\d{2}[A-Z]{3}\d{2}([A-Z]{6})$', date_teams)
    if not teams_match:
        return None

    teams_str = teams_match.group(1)

    # Split into two 3-letter abbreviations
    if len(teams_str) != 6:
        return None

    team1_abbr = teams_str[:3].lower()
    team2_abbr = teams_str[3:].lower()

    # Map sport_key to sport name for team_mapper
    sport_map = {
        'basketball_nba': 'NBA',
        'americanfootball_nfl': 'NFL',
        'americanfootball_ncaaf': 'NCAAF',
        'icehockey_nhl': 'NHL',
        'baseball_mlb': 'MLB'
    }
    sport_name = sport_map.get(sport_key, 'NBA')

    # Normalize team names
    team1 = normalize_team_name(team1_abbr, sport_name)
    team2 = normalize_team_name(team2_abbr, sport_name)

    if not team1 or not team2:
        return None

    return (team1, team2)


def compute_popularity(market: dict, max_v24h: int, max_oi: int) -> float:
    """
    Compute blended popularity score from volume_24h and open_interest.
    Normalized against max values for current batch.
    """
    v24h = market.get("volume_24h", 0) or 0
    oi = market.get("open_interest", 0) or 0

    # Avoid division by zero
    norm_v24h = v24h / max_v24h if max_v24h else 0
    norm_oi = oi / max_oi if max_oi else 0

    # Simple weighted average
    return round((norm_v24h * 0.6) + (norm_oi * 0.4), 3)


def fetch_kalshi_consensus(sport_key: str, target_date: str):
    """
    Fetches public consensus for US sports with seasonal awareness and dynamic limits.
    Optimized to only fetch data for in-season sports with appropriate game counts.

    Args:
        sport_key: Sport identifier (e.g., 'americanfootball_nfl')
        target_date: Target date for grouping (YYYY-MM-DD)
    """
    # 1. Check if sport is in season
    if not SportConfig.is_in_season(sport_key):
        print(f"📡 Kalshi API: Skipping {sport_key.upper()} - out of season")
        return

    # 2. Get sport configuration
    config = SportConfig.KALSHI_CONFIG.get(sport_key)
    if not config:
        print(
            f"📡 Kalshi API: Skipping {sport_key} - no Kalshi config")
        return

    ticker = config.get("ticker")
    sport_name_upper = SportConfig.get_sport_name(sport_key)

    if not ticker:
        print(
            f"📡 Kalshi API: Skipping {sport_key} - no Kalshi ticker configured")
        return

    # 3. Get dynamic limit based on day of week
    dynamic_limit = SportConfig.get_dynamic_limit(sport_key)
    if dynamic_limit == 0:
        print(
            f"📡 Kalshi API: Skipping {sport_key.upper()} - no games expected today")
        return

    print(
        f"📡 Kalshi API: Fetching {sport_name_upper} markets (limit: {dynamic_limit})...")

    client = KalshiClient()
    now_utc = datetime.now(timezone.utc)

    # 4. Fetch markets from multiple series (for NBA: moneyline, spread, total)
    all_markets = []
    series_tickers = [ticker]

    # Add additional tickers if available (e.g., NBA has spread and total)
    if "ticker_spread" in config:
        series_tickers.append(config["ticker_spread"])
    if "ticker_total" in config:
        series_tickers.append(config["ticker_total"])

    for series_ticker in series_tickers:
        markets_params = {
            "series_ticker": series_ticker,
            "status": "open",
            "limit": min(dynamic_limit * 3, 200)
        }

        markets_response = client.request(
            "GET", "/markets", params=markets_params)
        if markets_response:
            data = markets_response.json()
            markets = data.get("markets", [])
            all_markets.extend(markets)

    market_count_raw = len(all_markets)

    # 5. Filter for games happening soon (progressive time-based filtering)
    # CRITICAL FIX: Kalshi markets close AFTER the game ends (weeks later),
    # so we need to extract game date from ticker, not use close_time

    # Progressive filtering: Start with 12 hours, expand to 24h, then 48h if needed
    # This matches user preference for AI picks time-based filtering
    now_utc = datetime.now(timezone.utc)

    # Calculate date ranges for progressive filtering
    max_48h = now_utc + timedelta(hours=48)

    # For NFL: extend to 2 days for Thu/Sun/Mon games
    if sport_key == "americanfootball_nfl":
        max_48h = now_utc + timedelta(days=2)

    filtered_markets = []
    date_parse_failures = 0
    date_filter_failures = 0

    for m in all_markets:
        ticker = m.get("ticker", "")
        game_date_str = extract_game_date_from_ticker(ticker)

        if not game_date_str:
            date_parse_failures += 1
            continue

        try:
            # Parse game date (YYYY-MM-DD) and treat as end of day UTC
            game_date = datetime.strptime(game_date_str, '%Y-%m-%d')
            game_date = game_date.replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc)

            # Progressive filtering: include games within 48 hours
            # (AI picks will do its own 12h/24h filtering)
            if now_utc <= game_date <= max_48h:
                filtered_markets.append(m)
            else:
                date_filter_failures += 1
        except (ValueError, AttributeError):
            date_parse_failures += 1
            continue

    # Debug output
    if date_parse_failures > 0 or date_filter_failures > 0:
        print(
            f"🔍 Kalshi Debug: {date_parse_failures} date parse failures, {date_filter_failures} filtered out (outside 48h window)")
        if date_filter_failures > 0 and len(all_markets) > 0:
            # Show sample of filtered dates
            sample_ticker = all_markets[0].get("ticker", "")
            sample_date = extract_game_date_from_ticker(sample_ticker)
            print(
                f"🔍 Kalshi Debug: Sample ticker: {sample_ticker}, extracted date: {sample_date}")
            print(
                f"🔍 Kalshi Debug: Current time: {now_utc.strftime('%Y-%m-%d %H:%M UTC')}, Max time: {max_48h.strftime('%Y-%m-%d %H:%M UTC')}")

    # 6. Sort by game date (extracted from ticker)
    filtered_markets.sort(
        key=lambda m: extract_game_date_from_ticker(m.get("ticker", "")) or "")

    print(
        f"📡 Kalshi API: Found {market_count_raw} raw markets, "
        f"{len(filtered_markets)} for games in next 48h "
        f"for {sport_key.upper()}"
    )

    if not filtered_markets:
        print("⚠️ No upcoming markets found after filtering")
        return

    # 7. Calculate popularity scores
    max_v24h = max((m.get("volume_24h", 0) or 0)
                   for m in filtered_markets) or 1
    max_oi = max((m.get("open_interest", 0) or 0)
                 for m in filtered_markets) or 1

    stored_count = 0

    # 8. Process and store markets
    for m in filtered_markets:
        market_ticker = m.get("ticker")
        last_price = m.get("last_price")

        # Skip if price is missing (no liquidity/no consensus)
        if last_price is None or market_ticker is None:
            continue

        # Extract teams from ticker to create unified game_id
        teams = extract_teams_from_kalshi_ticker(market_ticker, sport_key)
        game_date = extract_game_date_from_ticker(market_ticker)

        if not teams or not game_date:
            # Fallback to ticker as game_id if parsing fails
            game_id = market_ticker
        else:
            # Create unified game_id matching other scrapers
            away_team, home_team = teams
            game_id = create_game_id(
                away_team, home_team, sport_name_upper, game_date)

        implied_prob = round(last_price / 100.0, 3)
        popularity_score = compute_popularity(m, max_v24h, max_oi)

        context_data = {
            "market_title": m.get("title"),
            "implied_prob_yes": implied_prob,
            "implied_prob_no": round(1.0 - implied_prob, 3),
            "market_ticker": market_ticker,
            "market_close": m.get("close_time"),
            "volume_24h": m.get("volume_24h", 0),
            "open_interest": m.get("open_interest", 0),
            "popularity_score": popularity_score,
        }

        # Store context with unified game_id for proper source aggregation
        insert_context(
            category="realtime",
            context_type="public_consensus",
            game_id=game_id,
            match_date=target_date,
            sport=sport_name_upper,  # Use sport name, not ticker
            data=context_data,
            source="kalshi",
        )
        stored_count += 1

    print(
        f"✅ Kalshi API: Stored {stored_count} markets for {sport_name_upper}")
