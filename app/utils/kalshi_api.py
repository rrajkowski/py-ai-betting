from datetime import datetime, timezone
import requests
from app.utils.db import insert_context
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

    def request(self, method: str, path: str, params: dict | None = None) -> requests.Response | None:
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
    Fetches public consensus for US sports (NFL, NCAAF, MLB, NBA) and stores them in DB.
    """
    # 1. Map internal sport key to Kalshi series ticker
    sport_map = {
        "americanfootball_nfl": {"ticker": "KXNFLGAME", "limit": 16},
        "americanfootball_ncaaf": {"ticker": "KXNCAAFGAME", "limit": 30},
        "baseball_mlb": {"ticker": "KXMLBGAME", "limit": 4},
        "basketball_nba": {"ticker": "KXNBAGAME", "limit": 12},
    }

    sport_info = sport_map.get(sport_key.lower())

    if not sport_info:
        print(
            f"📡 Kalshi API: Skipping {sport_key}. Series ticker unsupported."
        )
        return

    client = KalshiClient()

    # NOTE: Kalshi uses 'series_ticker' to group related events (e.g., all NFL markets)
    markets_params = {"series_ticker": sport_info["ticker"], "status": "open"}
    print(
        f"📡 Kalshi API: Fetching open markets for series {sport_info['ticker']}..."
    )
    markets_response = client.request("GET", "/markets", params=markets_params)

    if not markets_response:
        return

    data = markets_response.json()
    markets = data.get("markets", [])
    market_count_raw = len(markets)

    # --- Filter for future markets and process ---
    now_utc = datetime.now(timezone.utc)

    # CRITICAL: Filter markets to only include those that close in the future
    # This comparison unifies the date format: ISO string is converted to a UTC datetime object for comparison.
    markets = [
        m for m in markets
        if m.get("close_time")
        and datetime.fromisoformat(m["close_time"].replace("Z", "+00:00")) > now_utc
    ]

    print(
        f"📡 Kalshi API: Found {market_count_raw} raw markets, {len(markets)} closing in the future for {sport_key.upper()}"
    )

    if not markets:
        print("⚠️ No markets found after filtering for future close times.")
        return

    # Sanitize volumes / open_interest
    max_v24h = max((m.get("volume_24h", 0) or 0) for m in markets) or 1
    max_oi = max((m.get("open_interest", 0) or 0) for m in markets) or 1

    for m in markets:
        market_id = m.get("ticker")
        last_price = m.get("last_price")

        # Skip if price is missing (no liquidity/no consensus)
        if last_price is None:
            continue

        implied_prob = round(last_price / 100.0, 3)
        popularity_score = compute_popularity(m, max_v24h, max_oi)

        context_data = {
            "market_title": m.get("title"),
            "implied_prob_yes": implied_prob,
            "implied_prob_no": round(1.0 - implied_prob, 3),
            "market_ticker": market_id,
            # Use close_time, which is an ISO 8601 string, for date unification
            "market_close": m.get("close_time"),
            "volume_24h": m.get("volume_24h", 0),
            "open_interest": m.get("open_interest", 0),
            "popularity_score": popularity_score,
        }

        # Store context
        insert_context(
            category="realtime",
            context_type="public_consensus",
            game_id=market_id,
            match_date=target_date,  # Uses the grouping date (YYYY-MM-DD)
            sport=sport_info["ticker"],
            data=context_data,
            source="kalshi",
        )

    print(
        f"✅ Kalshi API: Stored public consensus data for {sport_info['ticker']} markets."
    )
