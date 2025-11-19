"""Check for recently closed Kalshi NBA markets (today's games)."""

import requests
from datetime import datetime, timezone, timedelta

API_URL = "https://api.elections.kalshi.com/trade-api/v2"

print("=" * 80)
print("KALSHI RECENTLY CLOSED NBA MARKETS")
print("=" * 80)

now_utc = datetime.now(timezone.utc)
start_of_today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

print(f"\n📅 Current time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
print(f"📅 Start of today: {start_of_today.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Try to get closed markets
print(f"\n{'=' * 80}")
print("Fetching CLOSED NBA single game markets...")
print("=" * 80)

try:
    response = requests.get(
        f"{API_URL}/markets",
        params={
            "series_ticker": "KXMVENBASINGLEGAME",
            "limit": 100,
            "status": "closed"  # Get closed markets
        },
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        markets = data.get("markets", [])
        
        print(f"✅ Found {len(markets)} closed markets")
        
        # Filter for markets that closed today
        today_closed = []
        for m in markets:
            close_time_str = m.get("close_time")
            if not close_time_str:
                continue
            
            try:
                close_time = datetime.fromisoformat(close_time_str.replace("Z", "+00:00"))
                if start_of_today <= close_time <= now_utc:
                    today_closed.append(m)
            except:
                pass
        
        print(f"✅ Found {len(today_closed)} markets that closed today")
        
        if len(today_closed) > 0:
            print("\n📊 Markets that closed today:")
            for i, m in enumerate(today_closed[:10], 1):
                ticker = m.get("ticker", "N/A")
                title = m.get("title", "N/A")
                close_time = m.get("close_time", "N/A")
                
                print(f"\n{i}. {ticker}")
                print(f"   Title: {title}")
                print(f"   Close: {close_time}")
        else:
            print("\n⚠️ No markets closed today")
            print("\nMost recent closed markets:")
            for i, m in enumerate(markets[:5], 1):
                print(f"\n{i}. {m.get('ticker')}")
                print(f"   Title: {m.get('title')[:70]}")
                print(f"   Close: {m.get('close_time')}")
    else:
        print(f"❌ HTTP {response.status_code}: {response.text[:200]}")

except Exception as e:
    print(f"❌ Error: {e}")

# Also check what statuses are available
print(f"\n{'=' * 80}")
print("Checking all available statuses...")
print("=" * 80)

statuses = ["open", "closed", "settled", "active"]

for status in statuses:
    try:
        response = requests.get(
            f"{API_URL}/markets",
            params={
                "series_ticker": "KXMVENBASINGLEGAME",
                "limit": 5,
                "status": status
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            markets = data.get("markets", [])
            print(f"✅ Status '{status}': {len(markets)} markets found")
            
            if len(markets) > 0:
                m = markets[0]
                print(f"   Sample: {m.get('title')[:60]}")
                print(f"   Close: {m.get('close_time')}")
        else:
            print(f"❌ Status '{status}': HTTP {response.status_code}")
    
    except Exception as e:
        print(f"❌ Status '{status}': Error - {e}")

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)

