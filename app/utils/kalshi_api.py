import requests
from app.utils.db import insert_context
from dotenv import load_dotenv

load_dotenv()


class KalshiClient:
    """
    Kalshi API client wrapper for public market data requests only (no auth).
    """

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

    v24h_norm = v24h / max_v24h if max_v24h > 0 else 0
    oi_norm = oi / max_oi if max_oi > 0 else 0

    # Weighted blend: 60% recent buzz, 40% sustained interest
    return round(0.6 * v24h_norm + 0.4 * oi_norm, 4)


def fetch_kalshi_consensus(sport_key: str, target_date: str):
    """
    Fetches public consensus for US sports (NFL, NCAAF) and stores them in DB.
    MLB is excluded (futures only, not per-game).
    """
    sport_map = {
        "americanfootball_nfl": {"ticker": "KXNFLGAME", "limit": 16},
        "americanfootball_ncaaf": {"ticker": "KXNCAAFGAME", "limit": 50},
        # MLB removed (only futures, not supported here)
    }

    sport_info = sport_map.get(sport_key.lower())
    if not sport_info:
        print(
            f"📡 Kalshi API: Skipping {sport_key}. Series ticker unsupported.")
        return

    client = KalshiClient()
    markets_params = {
        "series_ticker": sport_info["ticker"],
        "status": "open",
        "limit": sport_info["limit"],
    }

    print(f"📡 Kalshi API: Fetching open markets for {sport_info['ticker']}...")
    markets_response = client.request("GET", "/markets", params=markets_params)

    if not markets_response:
        return

    data = markets_response.json()
    markets = data.get("markets", [])
    market_count = len(markets)
    print(f"📡 Kalshi API: Found {market_count} active markets.")

    # Find max values for normalization
    max_v24h = max((m.get("volume_24h", 0) or 0)
                   for m in markets) if markets else 1
    max_oi = max((m.get("open_interest", 0) or 0)
                 for m in markets) if markets else 1

    for market in markets:
        market_id = market.get("ticker")
        last_price = market.get("last_price")

        if last_price is not None:
            implied_prob = last_price / 100.0
            popularity_score = compute_popularity(market, max_v24h, max_oi)

            context_data = {
                "market_title": market.get("title"),
                "implied_prob_yes": implied_prob,
                "implied_prob_no": 1.0 - implied_prob,
                "market_ticker": market_id,
                "market_close": market.get("close_ts"),
                "volume_24h": market.get("volume_24h", 0),
                "open_interest": market.get("open_interest", 0),
                "popularity_score": popularity_score,
            }

            insert_context(
                category="realtime",
                context_type="public_consensus",
                game_id=market_id,
                match_date=target_date,
                sport=sport_info["ticker"],
                data=context_data,
                source="kalshi",
            )

    print(
        f"✅ Kalshi API: Stored public consensus data for {sport_info['ticker']} markets."
    )
