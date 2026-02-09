#!/usr/bin/env python3
"""
Test script to verify Boyd's Bets NCAA-B and NCAA-F picks are being scraped correctly.
"""
from datetime import datetime
from app.utils.scraper import scrape_boydsbets_picks
from app.db import get_db


def test_boyds_ncaa_picks():
    """Test Boyd's Bets scraper for NCAA-B and NCAA-F picks."""
    target_date = datetime.now().strftime('%Y-%m-%d')

    print(f"\n{'='*80}")
    print(f"Testing Boyd's Bets NCAA Picks on {target_date}")
    print(f"{'='*80}\n")

    # Test NCAA Football (NCAA-F)
    print("🏈 Testing NCAA Football (NCAA-F)...")
    print("-" * 80)
    try:
        scrape_boydsbets_picks(target_date, 'americanfootball_ncaaf')
        print("✅ NCAA Football scraper completed\n")
    except Exception as e:
        print(f"❌ NCAA Football scraper failed: {e}\n")

    # Test NCAA Basketball (NCAA-B)
    print("🏀 Testing NCAA Basketball (NCAA-B)...")
    print("-" * 80)
    try:
        scrape_boydsbets_picks(target_date, 'basketball_ncaab')
        print("✅ NCAA Basketball scraper completed\n")
    except Exception as e:
        print(f"❌ NCAA Basketball scraper failed: {e}\n")

    # Check database for results
    print("🔍 Checking database for Boyd's Bets NCAA picks...")
    print("-" * 80)
    with get_db() as conn:
        cur = conn.cursor()

        # Check NCAA Football picks
        cur.execute("""
            SELECT COUNT(*) FROM prompt_context
            WHERE context_type = 'boydsbets_pick'
            AND source = 'boydsbets'
            AND sport = 'NCAAF'
            AND date(created_at) = date('now')
        """)
        ncaaf_count = cur.fetchone()[0]

        # Check NCAA Basketball picks
        cur.execute("""
            SELECT COUNT(*) FROM prompt_context
            WHERE context_type = 'boydsbets_pick'
            AND source = 'boydsbets'
            AND sport = 'NCAAB'
            AND date(created_at) = date('now')
        """)
        ncaab_count = cur.fetchone()[0]

        # Show sample picks
        print("\n📊 Results:")
        print(f"   NCAA Football (NCAAF): {ncaaf_count} picks")
        print(f"   NCAA Basketball (NCAAB): {ncaab_count} picks")

        if ncaaf_count > 0:
            print("\n🏈 Sample NCAA Football picks:")
            cur.execute("""
                SELECT game_id, team_pick, data FROM prompt_context
                WHERE context_type = 'boydsbets_pick'
                AND source = 'boydsbets'
                AND sport = 'NCAAF'
                AND date(created_at) = date('now')
                LIMIT 5
            """)
            for row in cur.fetchall():
                print(f"   - {row[0]}: {row[1]} ({row[2]})")

        if ncaab_count > 0:
            print("\n🏀 Sample NCAA Basketball picks:")
            cur.execute("""
                SELECT game_id, team_pick, data FROM prompt_context
                WHERE context_type = 'boydsbets_pick'
                AND source = 'boydsbets'
                AND sport = 'NCAAB'
                AND date(created_at) = date('now')
                LIMIT 5
            """)
            for row in cur.fetchall():
                print(f"   - {row[0]}: {row[1]} ({row[2]})")

    # Summary
    print(f"\n{'='*80}")
    if ncaaf_count > 0 or ncaab_count > 0:
        print("✅ SUCCESS: Boyd's Bets NCAA picks are being scraped!")
    else:
        print("⚠️  WARNING: No NCAA picks found. This could mean:")
        print("   1. No NCAA games today")
        print("   2. Boyd's Bets hasn't posted picks yet")
        print("   3. The scraper needs debugging")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_boyds_ncaa_picks()
