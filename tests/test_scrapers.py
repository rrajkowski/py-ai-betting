#!/usr/bin/env python3
"""
Test script to verify scrapers and Kalshi API are working correctly.
"""
import sys
from datetime import datetime
from app.utils.scraper import run_scrapers
from app.utils.kalshi_api import fetch_kalshi_consensus
from app.db import get_db


def test_scrapers_for_sport(sport_key: str):
    """Test all scrapers for a specific sport."""
    target_date = datetime.now().strftime('%Y-%m-%d')

    print(f"\n{'='*60}")
    print(f"Testing scrapers for {sport_key.upper()} on {target_date}")
    print(f"{'='*60}\n")

    # Test scrapers
    print("🔍 Running scrapers (OddsShark, OddsTrader, CBS Sports)...")
    try:
        run_scrapers(target_date, sport_key)
        print("✅ Scrapers completed\n")
    except Exception as e:
        print(f"❌ Scrapers failed: {e}\n")

    # Test Kalshi API
    print("🔍 Running Kalshi API...")
    try:
        fetch_kalshi_consensus(sport_key, target_date)
        print("✅ Kalshi API completed\n")
    except Exception as e:
        print(f"❌ Kalshi API failed: {e}\n")

    # Check database for results
    print("🔍 Checking database for today's data...")

    # Get sport name
    if '_' in sport_key:
        sport_name = sport_key.split('_')[-1].upper()
    else:
        sport_name = sport_key.upper()

    # Check each source
    sources = [
        ('oddsshark_pick', 'oddsshark'),
        ('oddstrader_pick', 'oddstrader'),
        ('cbs_expert_pick', 'cbs_sports'),
        ('public_consensus', 'kalshi'),
        ('expert_consensus', 'oddsshark')
    ]

    with get_db() as conn:
        cur = conn.cursor()
        for context_type, source in sources:
            cur.execute("""
                SELECT COUNT(*) FROM prompt_context
                WHERE context_type = ?
                AND source = ?
                AND sport = ?
                AND date(created_at) = date('now')
            """, (context_type, source, sport_name))
            count = cur.fetchone()[0]

            status = "✅" if count > 0 else "❌"
            print(f"{status} {context_type} ({source}): {count} records")

    print()


if __name__ == "__main__":
    # Test all sports
    sports = [
        'basketball_nba',
        'basketball_ncaab',
        'americanfootball_nfl',
        'americanfootball_ncaaf'
    ]

    if len(sys.argv) > 1:
        # Test specific sport if provided
        sport = sys.argv[1]
        test_scrapers_for_sport(sport)
    else:
        # Test all sports
        for sport in sports:
            test_scrapers_for_sport(sport)
