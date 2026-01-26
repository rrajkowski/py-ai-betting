#!/usr/bin/env python3
"""
Grade UFC picks using UFC Stats scraper (fallback when Odds API lacks data).

Usage:
    python3 scripts/grade_ufc_picks_from_stats.py <event_url>
    
Example:
    python3 scripts/grade_ufc_picks_from_stats.py http://ufcstats.com/event-details/00e11b5c8b7bfeeb
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.utils.ufc_stats_scraper import (
    process_ufc_event,
    scrape_ufc_event,
    find_pending_ufc_picks,
    match_fight_to_pick,
    grade_pick_from_fight,
    update_pick_result,
    update_historical_games
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/grade_ufc_picks_from_stats.py <event_url>")
        print("\nExample:")
        print("  python3 scripts/grade_ufc_picks_from_stats.py http://ufcstats.com/event-details/00e11b5c8b7bfeeb")
        print("\nThis script will:")
        print("  1. Scrape the UFC Stats event page")
        print("  2. Find all pending UFC picks in the database")
        print("  3. Match fights to picks")
        print("  4. Grade the picks and update the database")
        print("  5. Store fight results in historical_games table")
        sys.exit(1)
    
    event_url = sys.argv[1]
    
    print("\n" + "=" * 70)
    print("UFC STATS SCRAPER - FALLBACK SCORING")
    print("=" * 70)
    
    # Scrape the event
    print(f"\n1. Scraping UFC event: {event_url}")
    event_data = scrape_ufc_event(event_url)
    
    if not event_data['fights']:
        print("❌ No fights found in event")
        sys.exit(1)
    
    print(f"✅ Found {len(event_data['fights'])} fights")
    print(f"   Event date: {event_data['event_date']}")
    
    # Get pending picks
    print("\n2. Finding pending UFC picks...")
    pending_picks = find_pending_ufc_picks()
    print(f"✅ Found {len(pending_picks)} pending UFC picks")
    
    if not pending_picks:
        print("   No pending picks to grade")
        sys.exit(0)
    
    # Match and grade
    print("\n3. Matching fights to picks and grading...")
    graded = 0
    skipped = 0
    
    for fight in event_data['fights']:
        for pick in pending_picks[:]:  # Use slice to allow removal during iteration
            if match_fight_to_pick(fight, pick):
                result = grade_pick_from_fight(pick, fight)
                
                if result != 'Pending':
                    update_pick_result(pick['id'], result)
                    update_historical_games(fight)
                    
                    print(f"\n   ✅ Pick #{pick['id']}: {pick['game']}")
                    print(f"      Pick: {pick['pick']}")
                    print(f"      Result: {result}")
                    print(f"      Winner: {fight['winner']}")
                    
                    graded += 1
                    pending_picks.remove(pick)
                else:
                    skipped += 1
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Graded: {graded} picks")
    print(f"Skipped: {skipped} picks")
    print(f"Remaining pending: {len(pending_picks)} picks")
    
    if graded > 0:
        print(f"\n✅ Successfully graded {graded} UFC picks!")
    else:
        print("\n⚠️ No picks were graded. Check if fights match pending picks.")
    
    sys.exit(0 if graded > 0 else 1)


if __name__ == "__main__":
    main()

