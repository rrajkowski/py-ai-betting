#!/usr/bin/env python3
"""Debug script to check Kalshi market close times and game dates."""

import requests
from datetime import datetime, timezone, timedelta
import re

API_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Fetch NBA markets
print("Fetching NBA markets from Kalshi...")
response = requests.get(
    f"{API_URL}/markets",
    params={
        "series_ticker": "KXNBAGAME",
        "status": "open",
        "limit": 100
    },
    timeout=15
)

if response.status_code == 200:
    data = response.json()
    markets = data.get("markets", [])

    print(f"\nFound {len(markets)} NBA markets")

    now_utc = datetime.now(timezone.utc)
    print(f"Current time (UTC): {now_utc}")
    print(f"Current date: {now_utc.strftime('%Y-%m-%d')}")

    # Parse game dates from ticker (format: KXNBAGAME-25DEC26BOSIND-BOS)
    games_by_date = {}
    for m in markets:
        ticker = m.get("ticker", "")
        # Extract date from ticker (e.g., "25DEC26" -> 2025-12-26)
        match = re.search(r'(\d{2})([A-Z]{3})(\d{2})', ticker)
        if match:
            year = f"20{match.group(1)}"
            month_str = match.group(2)
            day = match.group(3)

            # Convert month abbreviation to number
            months = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
                      "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}
            month = months.get(month_str, "01")

            game_date = f"{year}-{month}-{day}"

            if game_date not in games_by_date:
                games_by_date[game_date] = []
            games_by_date[game_date].append(m)

    print(f"\n📅 Games by date:")
    for date in sorted(games_by_date.keys())[:5]:  # Show first 5 dates
        count = len(games_by_date[date])
        print(f"   {date}: {count} markets")

        # Show sample market for today's games
        if date == now_utc.strftime('%Y-%m-%d'):
            print(f"\n   🏀 TODAY'S GAMES ({date}):")
            for m in games_by_date[date][:4]:  # Show first 4
                print(f"      {m.get('ticker')}")
                print(f"         Title: {m.get('title')}")
                print(f"         Close: {m.get('close_time')}")
                print(f"         Volume 24h: {m.get('volume_24h', 0)}")
                print(f"         Open Interest: {m.get('open_interest', 0)}")

    # Check if there are games today
    today = now_utc.strftime('%Y-%m-%d')
    if today in games_by_date:
        print(
            f"\n✅ Found {len(games_by_date[today])} markets for TODAY ({today})")
    else:
        print(f"\n❌ No markets found for TODAY ({today})")
        print(f"   Next available date: {min(games_by_date.keys())}")
else:
    print(f"Error: HTTP {response.status_code}")
