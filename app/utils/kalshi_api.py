from datetime import datetime, timezone, timedelta
from typing import Optional
import requests
from app.utils.db import insert_context
from app.utils.sport_config import SportConfig
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
    ticker = SportConfig.get_kalshi_ticker(sport_key)
    sport_name_upper = SportConfig.get_sport_name(
        sport_key)  # Get proper sport name

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

    # 4. Fetch markets with status filter
    markets_params = {
        "series_ticker": ticker,
        "status": "open",
        # Fetch extra to account for filtering
        "limit": min(dynamic_limit * 3, 200)
    }

    markets_response = client.request("GET", "/markets", params=markets_params)
    if not markets_response:
        return

    data = markets_response.json()
    markets = data.get("markets", [])
    market_count_raw = len(markets)

    # 5. Filter for upcoming games only (close time in next 7 days)
    max_future_date = now_utc + timedelta(days=7)

    filtered_markets = []
    for m in markets:
        close_time_str = m.get("close_time")
        if not close_time_str:
            continue

        try:
            close_time = datetime.fromisoformat(
                close_time_str.replace("Z", "+00:00"))
            # Only include markets closing between now and 7 days from now
            if now_utc < close_time <= max_future_date:
                filtered_markets.append(m)
        except (ValueError, AttributeError):
            continue

    # 6. Sort by close time (soonest first) and apply dynamic limit
    filtered_markets.sort(key=lambda m: m.get("close_time", ""))
    markets = filtered_markets[:dynamic_limit]

    print(
        f"📡 Kalshi API: Found {market_count_raw} raw markets, "
        f"{len(filtered_markets)} upcoming (next 7 days), "
        f"using top {len(markets)} for {sport_key.upper()}"
    )

    if not markets:
        print("⚠️ No upcoming markets found after filtering")
        return

    # 7. Calculate popularity scores
    max_v24h = max((m.get("volume_24h", 0) or 0) for m in markets) or 1
    max_oi = max((m.get("open_interest", 0) or 0) for m in markets) or 1

    stored_count = 0

    # 8. Process and store markets
    for m in markets:
        market_id = m.get("ticker")
        last_price = m.get("last_price")

        # Skip if price is missing (no liquidity/no consensus)
        if last_price is None or market_id is None:
            continue

        implied_prob = round(last_price / 100.0, 3)
        popularity_score = compute_popularity(m, max_v24h, max_oi)

        context_data = {
            "market_title": m.get("title"),
            "implied_prob_yes": implied_prob,
            "implied_prob_no": round(1.0 - implied_prob, 3),
            "market_ticker": market_id,
            "market_close": m.get("close_time"),
            "volume_24h": m.get("volume_24h", 0),
            "open_interest": m.get("open_interest", 0),
            "popularity_score": popularity_score,
        }

        # Store context with proper sport name (not ticker)
        insert_context(
            category="realtime",
            context_type="public_consensus",
            game_id=market_id,
            match_date=target_date,
            sport=sport_name_upper,  # Use sport name, not ticker
            data=context_data,
            source="kalshi",
        )
        stored_count += 1

    print(
        f"✅ Kalshi API: Stored {stored_count} markets for {sport_name_upper}")
