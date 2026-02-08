#!/usr/bin/env python3
"""
Generate NBA picks from command line.

Usage:
    python3 scripts/generate_nba_picks.py
"""

import sys
import os

# Add parent directory to path BEFORE imports
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

from datetime import datetime, timezone, timedelta
from app.rage_picks import fetch_odds, generate_ai_picks, fetch_historical_nba
from app.db import get_most_recent_pick_timestamp
from app.utils.context_builder import create_super_prompt_payload
from app.utils.scraper import run_scrapers
from app.utils.kalshi_api import fetch_kalshi_consensus


def generate_nba_picks():
    """Generate NBA picks."""

    print("\n" + "="*60)
    print("NBA PICK GENERATION")
    print("="*60)

    sport_key = "basketball_nba"
    sport_name = "NBA"

    # Use today's date as starting point
    now_utc = datetime.now(timezone.utc)
    target_date = now_utc.strftime('%Y-%m-%d')

    print(f"\n📅 Target Date: {target_date}")

    # Check if picks were generated recently
    last_pick_time = get_most_recent_pick_timestamp(sport_name)
    if last_pick_time:
        if last_pick_time.tzinfo is None:
            last_pick_time = last_pick_time.replace(tzinfo=timezone.utc)

        # Use 12 hour wait time for production
        wait_duration = timedelta(hours=12)
        next_run_time = last_pick_time + wait_duration
        time_to_wait = next_run_time - now_utc

        if time_to_wait > timedelta(0):
            hours, remainder = divmod(time_to_wait.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            print(
                f"⏳ Picks were generated recently. Please wait {int(hours)}h {int(minutes)}m before running again.")
            print(
                f"   Last generated: {last_pick_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            return

    # Step 1: Fetch expert consensus
    print("\n📊 Step 1: Fetching Expert Consensus...")
    try:
        run_scrapers(target_date, sport_key)
        print("   ✅ Expert Consensus Saved")
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")

    # Step 2: Fetch public consensus (Kalshi)
    print("\n📈 Step 2: Fetching Public Consensus...")
    try:
        fetch_kalshi_consensus(sport_key, target_date)
        print("   ✅ Public Consensus Saved")
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")

    # Step 3: Build AI context
    print("\n🔨 Step 3: Building AI Context...")
    context_payload = create_super_prompt_payload(target_date, sport_key)
    num_games = len(context_payload.get('games', []))
    print(f"   ✅ Context Built ({num_games} Games)")

    if num_games == 0:
        print("\n❌ No games found. Exiting.")
        return

    # Step 4: Fetch odds
    print("\n📡 Step 4: Fetching Odds...")
    raw_odds = fetch_odds(sport_key)

    if not raw_odds:
        print("   ❌ No upcoming games with odds found")
        return

    print(f"   ✅ Found {len(raw_odds)} games with odds")

    # Step 5: Filter odds by time window (24 hours for NBA)
    print("\n⏰ Step 5: Filtering by Time Window...")
    max_24h = now_utc + timedelta(hours=24)

    filtered_odds = []
    for game in raw_odds:
        try:
            game_time = datetime.fromisoformat(
                game['commence_time'].replace('Z', '+00:00'))
            if now_utc < game_time <= max_24h:
                filtered_odds.append(game)
        except (ValueError, KeyError):
            continue

    print(f"   ✅ {len(filtered_odds)} games in next 24 hours")

    if not filtered_odds:
        print("\n❌ No games in time window. Exiting.")
        return

    # Step 6: Fetch historical data
    print("\n📚 Step 6: Fetching Historical Data...")
    # Use first game's home team for historical context
    history_team = filtered_odds[0]['home_team'] if filtered_odds else None
    if history_team:
        history_data = fetch_historical_nba(history_team)
        print(f"   ✅ Loaded {len(history_data)} historical games")
    else:
        history_data = []
        print("   ⚠️ No team found for historical data")

    # Step 7: Generate AI picks
    print("\n🤖 Step 7: Generating AI Picks...")

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

    except Exception as e:
        print(f"\n❌ Error generating picks: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    generate_nba_picks()
