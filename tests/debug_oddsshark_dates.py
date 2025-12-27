#!/usr/bin/env python3
"""Debug OddsShark scraper to check what dates are being extracted."""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

url = "https://www.oddsshark.com/nba/computer-picks"

print(f"Fetching {url}...")
resp = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}, timeout=15)

soup = BeautifulSoup(resp.text, "html.parser")
containers = soup.select(".computer-picks-event-container")

print(f"\nFound {len(containers)} game containers")
print(f"Current time (UTC): {datetime.now(timezone.utc)}")

for i, container in enumerate(containers[:3], 1):  # Check first 3
    print(f"\n--- Game {i} ---")

    # Show HTML structure
    print("HTML snippet:")
    print(str(container)[:500])

    # Extract date - try multiple selectors
    date_tag = container.select_one(".computer-picks-event-date")
    print(f"\nDate tag found: {date_tag is not None}")
    if date_tag:
        print(f"Date tag HTML: {str(date_tag)[:200]}")
        print(f"Has data-event-date: {date_tag.has_attr('data-event-date')}")
        if date_tag.has_attr("data-event-date"):
            ts = int(date_tag["data-event-date"])
            game_datetime = datetime.fromtimestamp(ts, tz=timezone.utc)
            print(f"Timestamp: {ts}")
            print(f"Game datetime: {game_datetime}")

    # Extract teams
    teams_div = container.select_one(".computer-picks-event-teams")
    if teams_div:
        teams_text = teams_div.get_text(strip=True)
        print(f"Teams: {teams_text}")
