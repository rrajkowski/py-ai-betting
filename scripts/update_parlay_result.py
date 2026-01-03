#!/usr/bin/env python3
"""
Script to manually update parlay results.
Usage: python scripts/update_parlay_result.py <pick_id> <result>
Example: python scripts/update_parlay_result.py 123 Loss
"""

import sys
import sqlite3
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.db import get_db


def update_parlay_result(pick_id: int, result: str):
    """
    Manually update a parlay's result.
    
    Args:
        pick_id: The ID of the parlay pick to update
        result: The result to set (Win, Loss, or Push)
    """
    if result not in ['Win', 'Loss', 'Push']:
        print(f"❌ Invalid result: {result}. Must be Win, Loss, or Push.")
        return False
    
    conn = get_db()
    cur = conn.cursor()
    
    # Check if pick exists and is a parlay
    cur.execute("SELECT id, sport, market, result FROM ai_picks WHERE id = ?", (pick_id,))
    pick = cur.fetchone()
    
    if not pick:
        print(f"❌ Pick ID {pick_id} not found.")
        conn.close()
        return False
    
    pick_dict = dict(pick)
    
    if pick_dict['sport'] != 'PARLAY' or pick_dict['market'] != 'parlay':
        print(f"⚠️  Warning: Pick ID {pick_id} is not a parlay (sport={pick_dict['sport']}, market={pick_dict['market']})")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            conn.close()
            return False
    
    # Update the result
    cur.execute("UPDATE ai_picks SET result = ? WHERE id = ?", (result, pick_id))
    conn.commit()
    conn.close()
    
    print(f"✅ Updated pick ID {pick_id} to result: {result}")
    return True


def list_pending_parlays():
    """List all pending parlays."""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, game, pick, odds_american, result, commence_time 
        FROM ai_picks 
        WHERE sport = 'PARLAY' AND market = 'parlay' AND LOWER(result) = 'pending'
        ORDER BY commence_time DESC
    """)
    
    parlays = cur.fetchall()
    conn.close()
    
    if not parlays:
        print("No pending parlays found.")
        return
    
    print("\n📋 Pending Parlays:")
    print("-" * 80)
    for p in parlays:
        p_dict = dict(p)
        print(f"ID: {p_dict['id']}")
        print(f"  Games: {p_dict['game'][:100]}...")
        print(f"  Picks: {p_dict['pick'][:100]}...")
        print(f"  Odds: {p_dict['odds_american']:+d}")
        print(f"  Time: {p_dict['commence_time']}")
        print(f"  Result: {p_dict['result']}")
        print("-" * 80)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments - list pending parlays
        list_pending_parlays()
        print("\nUsage: python scripts/update_parlay_result.py <pick_id> <result>")
        print("Example: python scripts/update_parlay_result.py 123 Loss")
    elif len(sys.argv) == 3:
        # Update a specific parlay
        try:
            pick_id = int(sys.argv[1])
            result = sys.argv[2].capitalize()
            update_parlay_result(pick_id, result)
        except ValueError:
            print("❌ Invalid pick_id. Must be a number.")
            sys.exit(1)
    else:
        print("Usage: python scripts/update_parlay_result.py <pick_id> <result>")
        print("Example: python scripts/update_parlay_result.py 123 Loss")
        sys.exit(1)

