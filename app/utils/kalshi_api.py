from datetime import datetime, timezone
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
    Fetch public consensus for sports (NFL, NCAAF, MLB), only for upcoming markets.
    """
    sport_map = {
        "americanfootball_nfl": {"ticker": "KXNFLGAME", "limit": 16},
        "americanfootball_ncaaf": {"ticker": "KXNCAAFGAME", "limit": 30},
        "baseball_mlb": {"ticker": "KXMLBGAME", "limit": 10},
        "basketball_nba": {"ticker": "KXNBAGAME", "limit": 10},
    }

    sport_info = sport_map.get(sport_key.lower())
    if not sport_info:
        print(f"📡 Kalshi API: Skipping {sport_key} (unsupported).")
        return

    client = KalshiClient()

    # Define current timestamp as min_close_ts to exclude markets that already closed / live
    now_ts = int(datetime.now(timezone.utc).timestamp())

    params = {
        "series_ticker": sport_info["ticker"],
        "status": "open",
        "limit": sport_info["limit"],
        "min_close_ts": now_ts + 1,  # only markets closing in the future
    }

    resp = client.request("GET", "/markets", params=params)
    if not resp or resp.status_code != 200:
        print(
            f"⚠️ Kalshi API request failed for {sport_info['ticker']} ({resp})")
        return

    data = resp.json()
    markets = data.get("markets", [])
    print(
        f"📡 Kalshi API: Returned {len(markets)} markets after filtering future-close for {sport_key.upper()}")

    if not markets:
        print("⚠️ No markets found after filtering for future close times.")
        return

    # Sanitize volumes / open_interest
    max_v24h = max((m.get("volume_24h", 0) or 0) for m in markets) or 1
    max_oi = max((m.get("open_interest", 0) or 0) for m in markets) or 1

    for m in markets:
        last_price = m.get("last_price")
        if last_price is None:
            continue

        implied_prob = round(last_price / 100.0, 3)
        popularity_score = compute_popularity(m, max_v24h, max_oi)

        context_data = {
            "market_title": m.get("title"),
            "implied_prob_yes": implied_prob,
            "implied_prob_no": round(1.0 - implied_prob, 3),
            "market_ticker": m.get("ticker"),
            # check the field name (docs use close_time) :contentReference[oaicite:1]{index=1}
            "market_close": m.get("close_time") or m.get("close_time"),
            "volume_24h": m.get("volume_24h", 0),
            "open_interest": m.get("open_interest", 0),
            "popularity_score": popularity_score,
        }

        insert_context(
            category="realtime",
            context_type="public_consensus",
            game_id=m.get("ticker"),
            match_date=target_date,
            sport=sport_key,
            data=context_data,
            source="kalshi",
        )

    print(
        f"✅ Kalshi API: Stored {len(markets)} future-close markets for {sport_key.upper()}")
