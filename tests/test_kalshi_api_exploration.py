"""Explore Kalshi API to find individual game markets."""

import requests

API_URL = "https://api.elections.kalshi.com/trade-api/v2"

print("=" * 80)
print("KALSHI API EXPLORATION")
print("=" * 80)

# 1. Get all series to see what's available
print("\n1️⃣ Fetching all series...")
response = requests.get(f"{API_URL}/series", params={"limit": 200})
if response.status_code == 200:
    data = response.json()
    all_series = data.get("series", [])
    
    # Filter for sports-related series
    sports_series = []
    sports_keywords = ["nba", "nfl", "ncaa", "basketball", "football", "mlb", "nhl", "game", "win", "score"]
    
    for s in all_series:
        ticker = s.get("ticker", "").lower()
        title = s.get("title", "").lower()
        
        if any(keyword in ticker or keyword in title for keyword in sports_keywords):
            sports_series.append(s)
    
    print(f"✅ Found {len(sports_series)} sports-related series")
    print("\nTop 20 sports series:")
    for i, s in enumerate(sports_series[:20], 1):
        print(f"{i:2d}. {s.get('ticker'):20s} - {s.get('title')[:60]}")
else:
    print(f"❌ Failed to fetch series: {response.status_code}")

# 2. Try different approaches to find NBA game markets
print("\n" + "=" * 80)
print("2️⃣ Trying different search strategies for NBA games...")
print("=" * 80)

strategies = [
    {"series_ticker": "NBA"},
    {"series_ticker": "KXNBA"},
    {"series_ticker": "KXESPYNBA"},
    {"category": "sports"},
    {"category": "Sports"},
    {"category": "basketball"},
    {"category": "Basketball"},
    {"event_ticker": "NBA"},
    {"search": "NBA"},
    {"search": "basketball"},
]

for i, params in enumerate(strategies, 1):
    print(f"\n--- Strategy {i}: {params} ---")
    params_with_limit = {**params, "limit": 20, "status": "open"}
    
    try:
        response = requests.get(f"{API_URL}/markets", params=params_with_limit, timeout=10)
        if response.status_code == 200:
            data = response.json()
            markets = data.get("markets", [])
            print(f"✅ Found {len(markets)} markets")
            
            if len(markets) > 0:
                print("Sample markets:")
                for j, m in enumerate(markets[:3], 1):
                    ticker = m.get("ticker", "N/A")
                    title = m.get("title", "N/A")
                    close_time = m.get("close_time", "N/A")
                    print(f"  {j}. {ticker}")
                    print(f"     Title: {title[:70]}")
                    print(f"     Close: {close_time}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"❌ Error: {e}")

# 3. Check if there are any markets with "game" or "win" in the title
print("\n" + "=" * 80)
print("3️⃣ Searching for markets with 'game', 'win', 'score' keywords...")
print("=" * 80)

try:
    response = requests.get(f"{API_URL}/markets", params={"limit": 200, "status": "open"}, timeout=15)
    if response.status_code == 200:
        data = response.json()
        all_markets = data.get("markets", [])
        
        game_keywords = ["game", "win", "score", "vs", "beat", "defeat"]
        game_markets = []
        
        for m in all_markets:
            title = m.get("title", "").lower()
            ticker = m.get("ticker", "").lower()
            
            if any(keyword in title or keyword in ticker for keyword in game_keywords):
                game_markets.append(m)
        
        print(f"✅ Found {len(game_markets)} markets with game-related keywords")
        
        if len(game_markets) > 0:
            print("\nSample game-related markets:")
            for i, m in enumerate(game_markets[:10], 1):
                print(f"\n{i}. {m.get('ticker')}")
                print(f"   Title: {m.get('title')[:70]}")
                print(f"   Close: {m.get('close_time')}")
                print(f"   Series: {m.get('series_ticker', 'N/A')}")
    else:
        print(f"❌ HTTP {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("EXPLORATION COMPLETE")
print("=" * 80)

