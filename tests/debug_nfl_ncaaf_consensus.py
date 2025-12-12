#!/usr/bin/env python3
"""
Debug script to check consensus data for NFL and NCAAF.
"""

import json
from app.utils.db import get_db
from app.utils.context_builder import create_super_prompt_payload
from datetime import datetime, timezone
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def check_consensus_data(sport_key, sport_name):
    """Check what consensus data is available for a sport."""
    print("\n" + "="*80)
    print(f"CHECKING CONSENSUS DATA FOR {sport_name}")
    print("="*80)

    # Get target date
    now_utc = datetime.now(timezone.utc)
    target_date = now_utc.strftime('%Y-%m-%d')

    print(f"\n📅 Target Date: {target_date}")
    print(f"🕐 Current Time (UTC): {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")

    # Check prompt_context table
    print(f"\n🔍 Checking prompt_context table for {sport_key}...")
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT game_id, source, data, created_at
        FROM prompt_context
        WHERE sport = ? AND date(created_at) >= date('now', '-2 days')
        ORDER BY created_at DESC
    """, (sport_key,))

    rows = cur.fetchall()

    if not rows:
        print(
            f"   ❌ No consensus data found in prompt_context for {sport_key}")
        print(f"   This means scrapers found NO picks for {sport_name}")
    else:
        print(f"   ✅ Found {len(rows)} consensus entries")

        # Group by source
        by_source = {}
        for row in rows:
            game_id, source, data_json, created_at = row
            if source not in by_source:
                by_source[source] = []
            by_source[source].append({
                'game_id': game_id,
                'created_at': created_at,
                'data': json.loads(data_json) if data_json else {}
            })

        print(f"\n   📊 Breakdown by source:")
        for source, entries in by_source.items():
            print(f"      • {source}: {len(entries)} games")

            # Show sample data
            if entries:
                sample = entries[0]
                print(f"        Sample game: {sample['game_id']}")
                print(f"        Created: {sample['created_at']}")
                data = sample['data']
                if 'pick' in data:
                    print(f"        Pick: {data.get('pick')}")
                if 'confidence' in data:
                    print(f"        Confidence: {data.get('confidence')}")

    # Build context payload
    print(f"\n🔨 Building context payload...")
    try:
        context = create_super_prompt_payload(target_date, sport_key)
        games = context.get('games', [])

        if not games:
            print(f"   ❌ Context builder returned 0 games")
        else:
            print(f"   ✅ Context builder returned {len(games)} games")

            # Check how many games have consensus data
            games_with_consensus = 0
            for game in games:
                markets = game.get('markets', [])
                has_consensus = False

                for market in markets:
                    consensus = market.get('consensus', {})
                    if consensus.get('oddsshark') or consensus.get('oddstrader') or consensus.get('cbs'):
                        has_consensus = True
                        break

                if has_consensus:
                    games_with_consensus += 1

            print(
                f"   📊 Games with consensus data: {games_with_consensus}/{len(games)}")

            if games_with_consensus == 0:
                print(f"\n   ⚠️  NO GAMES HAVE CONSENSUS DATA!")
                print(f"   This is why AI is returning 0 picks.")
                print(f"\n   Possible reasons:")
                print(
                    f"   1. Scrapers found no 3-4 star picks for {sport_name} today")
                print(f"   2. Scrapers are failing silently")
                print(
                    f"   3. Games are too far in the future (scrapers only show picks for next 1-2 days)")
            else:
                # Show sample game with consensus
                for game in games:
                    markets = game.get('markets', [])
                    for market in markets:
                        consensus = market.get('consensus', {})
                        if consensus.get('oddsshark') or consensus.get('oddstrader') or consensus.get('cbs'):
                            print(f"\n   📋 Sample game with consensus:")
                            print(f"      Game: {game.get('game')}")
                            print(f"      Market: {market.get('key')}")
                            print(
                                f"      Consensus: {json.dumps(consensus, indent=8)}")
                            break
                    else:
                        continue
                    break

    except Exception as e:
        print(f"   ❌ Error building context: {e}")
        import traceback
        traceback.print_exc()

    conn.close()


if __name__ == "__main__":
    # Check NFL
    check_consensus_data("americanfootball_nfl", "NFL")

    # Check NCAAF
    check_consensus_data("americanfootball_ncaaf", "NCAAF")

    print("\n" + "="*80)
    print("DIAGNOSIS COMPLETE")
    print("="*80)
