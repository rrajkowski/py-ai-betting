"""Debug script to check Kalshi market close times."""

from datetime import datetime, timezone, timedelta
from app.utils.kalshi_api import KalshiClient

# Initialize Kalshi client (unauthenticated)
client = KalshiClient()

# First, let's see what series are available
print("🔍 Fetching all series from Kalshi...")
series_response = client.request("GET", "/series", params={"limit": 200})

if series_response:
    series_data = series_response.json()
    all_series = series_data.get("series", [])

    print(f"\n📊 Found {len(all_series)} total series\n")
    print("=" * 80)
    print("SPORTS-RELATED SERIES:")
    print("=" * 80)

    sports_keywords = ["nba", "nfl", "ncaa",
                       "basketball", "football", "mlb", "nhl"]
    for s in all_series:
        ticker = s.get("ticker", "")
        title = s.get("title", "")

        # Check if it's sports-related
        if any(keyword in ticker.lower() or keyword in title.lower() for keyword in sports_keywords):
            print(f"\nTicker: {ticker}")
            print(f"Title: {title}")

    print("\n" + "=" * 80)

# Now fetch NBA markets
print("\n🔍 Fetching NBA markets from Kalshi...")
response = client.request("GET", "/markets", params={
    "series_ticker": "NBA",
    "status": "open",
    "limit": 30
})

if not response:
    print("❌ No response from Kalshi API")
    exit(1)

data = response.json()
markets = data.get("markets", [])

print(f"\n📊 Found {len(markets)} NBA markets with series_ticker='NBA'\n")

now_utc = datetime.now(timezone.utc)
max_future_date = now_utc + timedelta(days=3)

print(f"⏰ Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(
    f"⏰ Max future date (UTC): {max_future_date.strftime('%Y-%m-%d %H:%M:%S')}\n")

print("=" * 80)
print("MARKET CLOSE TIMES:")
print("=" * 80)

for i, m in enumerate(markets[:10], 1):
    ticker = m.get("ticker", "N/A")
    title = m.get("title", "N/A")
    close_time_str = m.get("close_time", "N/A")

    if close_time_str != "N/A":
        try:
            close_time = datetime.fromisoformat(
                close_time_str.replace("Z", "+00:00"))

            # Check if it passes the filter
            passes_filter = now_utc < close_time <= max_future_date
            status = "✅ PASSES" if passes_filter else "❌ FILTERED OUT"

            # Calculate time until close
            time_until = close_time - now_utc
            hours_until = time_until.total_seconds() / 3600

            print(f"\n{i}. {ticker}")
            print(f"   Title: {title[:60]}...")
            print(
                f"   Close Time: {close_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"   Time Until Close: {hours_until:.1f} hours")
            print(f"   Filter Status: {status}")

            if not passes_filter:
                if close_time <= now_utc:
                    print("   Reason: Already closed")
                elif close_time > max_future_date:
                    print(
                        f"   Reason: Closes too far in future (>{hours_until:.1f} hours)")
        except Exception as e:
            print(f"\n{i}. {ticker}")
            print(f"   Error parsing close_time: {e}")
    else:
        print(f"\n{i}. {ticker}")
        print("   No close_time available")

print("\n" + "=" * 80)
