#!/usr/bin/env python3
"""
Generate MLB picks from command line.

Usage:
    python3 scripts/generate_mlb_picks.py
"""

import os
import sys
from datetime import UTC, datetime, timedelta

# Add parent directory to path BEFORE imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from app.picks import generate_ai_picks  # noqa: E402
from app.rage_picks import fetch_historical_mlb, fetch_odds, fetch_scores  # noqa: E402
from app.utils.context_builder import create_super_prompt_payload  # noqa: E402
from app.utils.kalshi_api import fetch_kalshi_consensus  # noqa: E402
from app.utils.scraper import run_scrapers  # noqa: E402


def generate_mlb_picks():
    """Generate MLB picks."""

    print("\n" + "="*60)
    print("MLB PICK GENERATION TEST")
    print("="*60)

    sport_key = "baseball_mlb"
    sport_name = "MLB"

    # Use today's date as starting point
    now_utc = datetime.now(UTC)
    target_date = now_utc.strftime('%Y-%m-%d')

    print(f"\n📅 Target Date: {target_date}")

    # Step 1: Test MLB scores API
    print("\n📡 Step 1: Testing MLB Scores API...")
    try:
        scores = fetch_scores(sport="baseball_mlb", days_from=2)
        print(f"   ✅ Found {len(scores)} MLB games in last 2 days")
        if scores:
            print(
                f"   Sample game: {scores[0].get('home_team')} vs {scores[0].get('away_team')}")
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")

    # Step 2: Fetch expert consensus
    print("\n📊 Step 2: Fetching Expert Consensus...")
    try:
        run_scrapers(target_date, sport_key)
        print("   ✅ Expert Consensus Saved")
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")

    # Step 3: Fetch public consensus (Kalshi)
    print("\n📈 Step 3: Fetching Public Consensus...")
    try:
        fetch_kalshi_consensus(sport_key, target_date)
        print("   ✅ Public Consensus Saved")
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")

    # Step 4: Build AI context
    print("\n🔨 Step 4: Building AI Context...")
    context_payload = create_super_prompt_payload(target_date, sport_key)
    num_games = len(context_payload.get('games', []))
    print(f"   ✅ Context Built ({num_games} Games)")

    if num_games == 0:
        print(
            "\n⚠️ No games found in context. This is expected if MLB season hasn't started.")
        print("   Continuing to test odds API...")

    # Step 5: Fetch odds
    print("\n📡 Step 5: Fetching MLB Odds...")
    raw_odds = fetch_odds(sport_key)

    if not raw_odds:
        print("   ⚠️ No upcoming MLB games with odds found")
        print("   This is expected if MLB season hasn't started (starts March 20)")
        return

    print(f"   ✅ Found {len(raw_odds)} games with odds")

    # Step 6: Filter odds by time window (48 hours for MLB)
    print("\n⏰ Step 6: Filtering by Time Window...")
    max_48h = now_utc + timedelta(hours=48)

    filtered_odds = []
    for game in raw_odds:
        try:
            game_time = datetime.fromisoformat(
                game['commence_time'].replace('Z', '+00:00'))
            if now_utc < game_time <= max_48h:
                filtered_odds.append(game)
        except (ValueError, KeyError):
            continue

    print(f"   ✅ {len(filtered_odds)} games in next 48 hours")

    if not filtered_odds:
        print("\n⚠️ No games in time window.")
        return

    # Step 7: Fetch historical data
    print("\n📚 Step 7: Fetching Historical Data...")
    # Use first game's home team for historical context
    history_team = filtered_odds[0]['home_team'] if filtered_odds else None
    if history_team:
        history_data = fetch_historical_mlb(history_team)
        print(
            f"   ✅ Loaded {len(history_data)} historical games for {history_team}")
    else:
        history_data = []
        print("   ⚠️ No team found for historical data")

    # Step 8: Generate AI picks
    print("\n🤖 Step 8: Generating AI Picks...")

    # Convert to DataFrame-like structure
    import pandas as pd
    odds_df = pd.DataFrame(filtered_odds)

    try:
        picks = generate_ai_picks(
            odds_df,
            history_data,
            sport=sport_name,
            context_payload=context_payload
        )

        if picks:
            print(f"\n✅ Generated {len(picks)} picks!")
            for i, pick in enumerate(picks, 1):
                print(f"\n   Pick {i}:")
                print(f"      Game: {pick.get('game')}")
                print(f"      Pick: {pick.get('pick')}")
                print(f"      Market: {pick.get('market')}")
                print(f"      Odds: {pick.get('odds_american')}")
                print(f"      Confidence: {pick.get('confidence')} stars")
        else:
            print("\n⚠️ No picks generated")
            print(
                "   This could be due to lack of consensus data or no high-value picks found")

    except Exception as e:
        print(f"\n❌ Error generating picks: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    generate_mlb_picks()
