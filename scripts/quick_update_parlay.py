#!/usr/bin/env python3
"""Quick script to update the Jan 2nd parlay result."""

import sqlite3

# Connect to database
conn = sqlite3.connect('bets.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Find parlays from Jan 2nd
print("Looking for parlays from Jan 2nd...")
cur.execute("""
    SELECT id, game, pick, odds_american, result, commence_time 
    FROM ai_picks 
    WHERE sport = 'PARLAY' 
    AND date(commence_time) = '2026-01-02'
    ORDER BY id DESC
""")

parlays = cur.fetchall()

if not parlays:
    print("No parlays found from Jan 2nd, 2026")
    # Try without year
    cur.execute("""
        SELECT id, game, pick, odds_american, result, commence_time 
        FROM ai_picks 
        WHERE sport = 'PARLAY' 
        AND commence_time LIKE '%01-02%'
        ORDER BY id DESC
    """)
    parlays = cur.fetchall()

if parlays:
    print(f"\nFound {len(parlays)} parlay(s):")
    for p in parlays:
        p_dict = dict(p)
        print(f"\nID: {p_dict['id']}")
        print(f"  Games: {p_dict['game']}")
        print(f"  Picks: {p_dict['pick']}")
        print(f"  Odds: {p_dict['odds_american']:+d}")
        print(f"  Time: {p_dict['commence_time']}")
        print(f"  Current Result: {p_dict['result']}")
        
        # Update to Loss if pending
        if p_dict['result'].lower() == 'pending':
            print(f"\n  Updating to Loss...")
            cur.execute("UPDATE ai_picks SET result = 'Loss' WHERE id = ?", (p_dict['id'],))
            conn.commit()
            print(f"  ✅ Updated!")
else:
    print("No parlays found. Showing all parlays:")
    cur.execute("""
        SELECT id, game, pick, odds_american, result, commence_time 
        FROM ai_picks 
        WHERE sport = 'PARLAY'
        ORDER BY id DESC
        LIMIT 10
    """)
    all_parlays = cur.fetchall()
    for p in all_parlays:
        p_dict = dict(p)
        print(f"\nID: {p_dict['id']} | Time: {p_dict['commence_time']} | Result: {p_dict['result']}")

conn.close()
print("\nDone!")

