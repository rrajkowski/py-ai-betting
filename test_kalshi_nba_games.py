"""Test fetching NBA single game markets from Kalshi."""

import requests
from datetime import datetime, timezone, timedelta

API_URL = "https://api.elections.kalshi.com/trade-api/v2"

print("=" * 80)
print("KALSHI NBA SINGLE GAME MARKETS")
print("=" * 80)

# Get today's date range
now_utc = datetime.now(timezone.utc)
end_of_today = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)

print(f"\n📅 Current time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"📅 End of today: {end_of_today.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Try different series tickers for NBA games
series_tickers = [
    "KXMVENBASINGLEGAME",
    "KXMVESPORTSMULTIGAMEEXTENDED",
    "KXNBA",
]

for series_ticker in series_tickers:
    print(f"\n{'=' * 80}")
    print(f"Series: {series_ticker}")
    print("=" * 80)
    
    try:
        response = requests.get(
            f"{API_URL}/markets",
            params={
                "series_ticker": series_ticker,
                "limit": 50,
                "status": "open"
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            markets = data.get("markets", [])
            
            print(f"✅ Found {len(markets)} total markets")
            
            # Filter for today's games
            today_markets = []
            for m in markets:
                close_time_str = m.get("close_time")
                if not close_time_str:
                    continue
                
                try:
                    close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                    if now_utc < close_time <= end_of_today:
                        today_markets.append(m)
                except:
                    pass
            
            print(f"✅ Found {len(today_markets)} markets closing today")
            
            # Show details of today's markets
            if len(today_markets) > 0:
                print("\n📊 Today's Markets:")
                for i, m in enumerate(today_markets[:10], 1):
                    ticker = m.get("ticker", "N/A")
                    title = m.get("title", "N/A")
                    close_time = m.get("close_time", "N/A")
                    yes_price = m.get("yes_bid", "N/A")
                    volume = m.get("volume", 0)
                    
                    print(f"\n{i}. {ticker}")
                    print(f"   Title: {title}")
                    print(f"   Close: {close_time}")
                    print(f"   Yes Price: {yes_price} cents")
                    print(f"   Volume: {volume}")
            else:
                # Show some sample markets even if not today
                print("\n📊 Sample Markets (any date):")
                for i, m in enumerate(markets[:5], 1):
                    ticker = m.get("ticker", "N/A")
                    title = m.get("title", "N/A")
                    close_time = m.get("close_time", "N/A")
                    
                    print(f"\n{i}. {ticker}")
                    print(f"   Title: {title}")
                    print(f"   Close: {close_time}")
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

# Also try searching by category
print(f"\n{'=' * 80}")
print("Searching by category: 'Sports'")
print("=" * 80)

try:
    response = requests.get(
        f"{API_URL}/markets",
        params={
            "category": "Sports",
            "limit": 100,
            "status": "open"
        },
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        markets = data.get("markets", [])
        
        # Filter for NBA-related markets closing today
        nba_today = []
        for m in markets:
            title = m.get("title", "").lower()
            ticker = m.get("ticker", "").lower()
            close_time_str = m.get("close_time")
            
            # Check if it's NBA-related
            if "nba" in ticker or any(team in title for team in ["indiana", "portland", "denver", "miami", "cleveland"]):
                if close_time_str:
                    try:
                        close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                        if now_utc < close_time <= end_of_today:
                            nba_today.append(m)
                    except:
                        pass
        
        print(f"✅ Found {len(nba_today)} NBA markets closing today")
        
        for i, m in enumerate(nba_today[:10], 1):
            print(f"\n{i}. {m.get('ticker')}")
            print(f"   Title: {m.get('title')}")
            print(f"   Close: {m.get('close_time')}")
            print(f"   Yes Price: {m.get('yes_bid', 'N/A')} cents")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)

