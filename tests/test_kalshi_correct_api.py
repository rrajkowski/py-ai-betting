"""Test Kalshi API with correct approach for individual game markets."""

import requests
from datetime import datetime, timezone, timedelta
import json

API_URL = "https://api.elections.kalshi.com/trade-api/v2"

print("=" * 80)
print("KALSHI API - CORRECT APPROACH FOR NBA GAMES")
print("=" * 80)

now_utc = datetime.now(timezone.utc)
next_24h = now_utc + timedelta(hours=24)

print(f"\n📅 Current time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"📅 Next 24h: {next_24h.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Step 1: Get all NBA game events (not the multivariate markets)
print(f"\n{'=' * 80}")
print("Step 1: Fetching NBA GAME events (moneyline markets)")
print("=" * 80)

try:
    response = requests.get(
        f"{API_URL}/markets",
        params={
            "series_ticker": "KXNBAGAME",  # NBA game moneyline markets
            "limit": 50,
            "status": "open"
        },
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        markets = data.get("markets", [])
        
        print(f"✅ Found {len(markets)} NBA game markets")
        
        # Filter for games in next 24 hours
        upcoming_games = []
        for m in markets:
            close_time_str = m.get("close_time")
            if not close_time_str:
                continue
            
            try:
                close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                if now_utc < close_time <= next_24h:
                    upcoming_games.append(m)
            except:
                pass
        
        print(f"✅ Found {len(upcoming_games)} games in next 24 hours")
        
        if len(upcoming_games) > 0:
            print("\n📊 Upcoming games:")
            for i, m in enumerate(upcoming_games[:5], 1):
                ticker = m.get("ticker", "N/A")
                title = m.get("title", "N/A")
                close_time = m.get("close_time", "N/A")
                yes_bid = m.get("yes_bid", 0)
                
                print(f"\n{i}. {ticker}")
                print(f"   Title: {title}")
                print(f"   Close: {close_time}")
                print(f"   Yes Price: {yes_bid} cents ({yes_bid}% probability)")
        else:
            print("\n⚠️ No games in next 24 hours")
            print("\nShowing sample markets (any date):")
            for i, m in enumerate(markets[:3], 1):
                print(f"\n{i}. {m.get('ticker')}")
                print(f"   Title: {m.get('title')}")
                print(f"   Close: {m.get('close_time')}")
    else:
        print(f"❌ HTTP {response.status_code}: {response.text[:200]}")

except Exception as e:
    print(f"❌ Error: {e}")

# Step 2: Get NBA spread markets
print(f"\n{'=' * 80}")
print("Step 2: Fetching NBA SPREAD markets")
print("=" * 80)

try:
    response = requests.get(
        f"{API_URL}/markets",
        params={
            "series_ticker": "KXNBASPREAD",  # NBA spread markets
            "limit": 50,
            "status": "open"
        },
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        markets = data.get("markets", [])
        
        print(f"✅ Found {len(markets)} NBA spread markets")
        
        if len(markets) > 0:
            print("\nSample spread markets:")
            for i, m in enumerate(markets[:3], 1):
                print(f"\n{i}. {m.get('ticker')}")
                print(f"   Title: {m.get('title')}")
                print(f"   Close: {m.get('close_time')}")
    else:
        print(f"❌ HTTP {response.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")

# Step 3: Get NBA total markets
print(f"\n{'=' * 80}")
print("Step 3: Fetching NBA TOTAL markets")
print("=" * 80)

try:
    response = requests.get(
        f"{API_URL}/markets",
        params={
            "series_ticker": "KXNBATOTAL",  # NBA total markets
            "limit": 50,
            "status": "open"
        },
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        markets = data.get("markets", [])
        
        print(f"✅ Found {len(markets)} NBA total markets")
        
        if len(markets) > 0:
            print("\nSample total markets:")
            for i, m in enumerate(markets[:3], 1):
                print(f"\n{i}. {m.get('ticker')}")
                print(f"   Title: {m.get('title')}")
                print(f"   Close: {m.get('close_time')}")
    else:
        print(f"❌ HTTP {response.status_code}")

except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)

