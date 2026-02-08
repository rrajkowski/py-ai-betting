#!/usr/bin/env python3
"""
Manually update a UFC pick result when the Odds API doesn't have the data.

Usage:
    python3 scripts/update_ufc_pick_result.py <pick_id> <result>
    
Example:
    python3 scripts/update_ufc_pick_result.py 448 Win
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import get_db, update_pick_result


def manual_update_pick(pick_id: int, result: str):
    """
    Manually update a pick's result.
    
    Args:
        pick_id: The ID of the pick to update
        result: The result to set (Win, Loss, or Push)
    """
    if result not in ['Win', 'Loss', 'Push', 'Pending']:
        print(f"❌ Invalid result: {result}. Must be Win, Loss, Push, or Pending.")
        return False
    
    conn = get_db()
    cur = conn.cursor()
    
    # Check if pick exists
    cur.execute("SELECT id, game, sport, pick, market, result FROM ai_picks WHERE id = ?", (pick_id,))
    pick = cur.fetchone()
    
    if not pick:
        print(f"❌ Pick ID {pick_id} not found.")
        conn.close()
        return False
    
    pick_dict = dict(pick)
    old_result = pick_dict['result']
    
    print("\n📋 Pick Details:")
    print(f"   ID: {pick_id}")
    print(f"   Sport: {pick_dict['sport']}")
    print(f"   Game: {pick_dict['game']}")
    print(f"   Pick: {pick_dict['pick']}")
    print(f"   Market: {pick_dict['market']}")
    print(f"   Current Result: {old_result}")
    print(f"   New Result: {result}")
    
    # Update the result
    update_pick_result(pick_id, result)
    
    print(f"\n✅ Successfully updated pick ID {pick_id} from '{old_result}' to '{result}'")
    return True


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/update_ufc_pick_result.py <pick_id> <result>")
        print("Example: python3 scripts/update_ufc_pick_result.py 448 Win")
        sys.exit(1)
    
    try:
        pick_id = int(sys.argv[1])
        result = sys.argv[2]
        
        if manual_update_pick(pick_id, result):
            sys.exit(0)
        else:
            sys.exit(1)
    except ValueError:
        print(f"❌ Invalid pick_id: {sys.argv[1]}. Must be an integer.")
        sys.exit(1)

