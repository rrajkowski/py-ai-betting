#!/usr/bin/env python3
"""
Complete UFC scoring workflow test.
Demonstrates all three tiers of the grading system.
"""

from app.utils.ufc_stats_scraper import process_ufc_event
from app.db import get_db, update_pick_result
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


print("\n" + "=" * 70)
print("COMPLETE UFC SCORING WORKFLOW TEST")
print("=" * 70)

# Step 1: Check initial state
print("\n[STEP 1] Check initial pick state")
print("-" * 70)

with get_db() as conn:
    cur = conn.cursor()
    cur.execute("SELECT id, game, pick, result FROM ai_picks WHERE id=448")
    pick = cur.fetchone()

if pick:
    pick_dict = dict(pick)
    print(f"Pick #448 (Krylov):")
    print(f"  Game: {pick_dict['game']}")
    print(f"  Pick: {pick_dict['pick']}")
    print(f"  Current Result: {pick_dict['result']}")
else:
    print("❌ Pick #448 not found!")
    sys.exit(1)

# Step 2: Simulate Tier 1 failure (Odds API)
print("\n[STEP 2] Tier 1: Odds API (Simulated Failure)")
print("-" * 70)
print("Odds API returns: completed=false, scores=null")
print("❌ Tier 1 failed - falling back to Tier 2")

# Step 3: Use Tier 2 (UFC Stats Scraper)
print("\n[STEP 3] Tier 2: UFC Stats Scraper")
print("-" * 70)

event_url = "http://ufcstats.com/event-details/00e11b5c8b7bfeeb"
print(f"Scraping: {event_url}")

result = process_ufc_event(event_url)
print(f"✅ Graded {result['graded']} picks")

# Step 4: Verify update
print("\n[STEP 4] Verify Database Update")
print("-" * 70)

with get_db() as conn:
    cur = conn.cursor()
    cur.execute("SELECT id, game, pick, result FROM ai_picks WHERE id=448")
    pick = cur.fetchone()

if pick:
    pick_dict = dict(pick)
    print(f"Pick #448 (Krylov) - UPDATED:")
    print(f"  Game: {pick_dict['game']}")
    print(f"  Pick: {pick_dict['pick']}")
    print(f"  New Result: {pick_dict['result']}")

    if pick_dict['result'] == 'Win':
        print("\n✅ SUCCESS! Pick correctly graded as Win")
    else:
        print(f"\n❌ FAILED! Expected 'Win', got '{pick_dict['result']}'")
else:
    print("❌ Pick #448 not found!")

# Step 5: Show Tier 3 option
print("\n[STEP 5] Tier 3: Manual Update (Fallback)")
print("-" * 70)
print("If Tier 2 fails, use:")
print("  Option A: Admin panel - Click ✏️ Edit button")
print("  Option B: CLI - python3 scripts/update_ufc_pick_result.py 448 Win")

print("\n" + "=" * 70)
print("WORKFLOW TEST COMPLETE")
print("=" * 70)
