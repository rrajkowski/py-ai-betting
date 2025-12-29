#!/usr/bin/env python3
"""
Test the new time-based filtering logic.
"""

from datetime import datetime, timezone, timedelta
from app.ai_picks import fetch_odds
import sys
sys.path.insert(0, '.')


def test_time_filtering(sport_key, sport_name):
    """Test time-based filtering for a sport."""

    print(f"\n{'='*60}")
    print(f"{sport_name.upper()} TIME-BASED FILTERING TEST")
    print(f"{'='*60}")

    raw_odds = fetch_odds(sport_key)
    print(f"\n📡 Found {len(raw_odds)} total games from API")

    if not raw_odds:
        print("❌ No games available")
        return

    # Show all game times
    now_utc = datetime.now(timezone.utc)
    print(f"\n🕐 Current time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M')}")
    print("\n📅 All games:")
    for i, row in enumerate(raw_odds):
        game_time_str = row.get('commence_time', '')
        try:
            game_time = datetime.fromisoformat(
                game_time_str.replace('Z', '+00:00'))
            hours_away = (game_time - now_utc).total_seconds() / 3600
            print(f"   {i+1}. {row['away_team']} @ {row['home_team']}")
            print(
                f"      Time: {game_time.strftime('%Y-%m-%d %H:%M')} ({hours_away:.1f}h away)")
        except (ValueError, AttributeError):
            print(
                f"   {i+1}. {row['away_team']} @ {row['home_team']} (invalid time)")

    # Test different time windows
    time_windows = {
        "basketball_nba": [12, 24],
        "basketball_ncaab": [12, 24],
        "americanfootball_nfl": [24, 48, 72],
        "americanfootball_ncaaf": [24, 48],
        "icehockey_nhl": [12, 24],
    }

    windows = time_windows.get(sport_key, [12, 24])
    min_markets_threshold = 15

    print(f"\n🔍 Testing time windows: {windows} hours")
    print(f"   Minimum markets threshold: {min_markets_threshold}")

    for hours in windows:
        max_time = now_utc + timedelta(hours=hours)
        games_in_window = 0
        markets_count = 0

        for row in raw_odds:
            game_time_str = row.get('commence_time', '')
            try:
                game_time = datetime.fromisoformat(
                    game_time_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                continue

            if game_time > max_time:
                continue

            games_in_window += 1

            bookmaker = next((b for b in row.get("bookmakers", [])
                             if b["key"] == "draftkings"), None)
            if not bookmaker:
                continue

            for market in bookmaker.get("markets", []):
                market_key = market["key"]
                outcomes = market.get("outcomes", [])

                # For h2h, filter extreme odds
                if market_key == "h2h":
                    if len(outcomes) == 2:
                        odds1 = outcomes[0].get("price", 0)
                        odds2 = outcomes[1].get("price", 0)
                        if odds1 < -150 or odds1 > 150 or odds2 < -150 or odds2 > 150:
                            continue

                markets_count += len(outcomes)

        status = "✅ ENOUGH" if markets_count >= min_markets_threshold else "⚠️  TOO FEW"
        print(
            f"\n   {hours}h window: {games_in_window} games, {markets_count} markets {status}")

        if markets_count >= min_markets_threshold:
            print(f"   → Would use this window ({hours}h)")
            break


if __name__ == "__main__":
    # Test NBA
    test_time_filtering("basketball_nba", "NBA")

    # Test NCAAB
    test_time_filtering("basketball_ncaab", "NCAAB")

    # Test NFL (if available)
    test_time_filtering("americanfootball_nfl", "NFL")
