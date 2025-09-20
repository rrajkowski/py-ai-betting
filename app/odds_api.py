import os
import httpx
from dotenv import load_dotenv

load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4"


async def fetch_sports():
    url = f"{BASE_URL}/sports"
    params = {"apiKey": ODDS_API_KEY}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
    r.raise_for_status()
    return r.json()


async def fetch_odds(sport="soccer_epl", region="us", markets=None):
    if markets is None:
        markets = ["h2h", "spreads", "totals"]
    url = f"{BASE_URL}/sports/{sport}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": region,
        "markets": ",".join(markets),
        "oddsFormat": "decimal"
    }
    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)
    r.raise_for_status()
    return r.json()
