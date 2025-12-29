#!/usr/bin/env python3
"""
Debug script to investigate the Memphis Grizzlies @ Washington Wizards 5-star pick.
Checks what data was scraped from each source and how the AI made its decision.
"""

import sqlite3
import json

DB_PATH = "bets.db"

def main():
    print("=" * 80)
    print("INVESTIGATING: Memphis Grizzlies @ Washington Wizards - Over 239.5 (5 stars)")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Find the game in the database
    game_patterns = [
        "%Memphis Grizzlies @ Washington Wizards%",
        "%Grizzlies @ Wizards%",
        "%Memphis @ Washington%",
        "%MEM @ WAS%"
    ]
    
    print("\n1. SEARCHING FOR GAME IN PROMPT_CONTEXT TABLE")
    print("-" * 80)
    
    all_game_data = []
    for pattern in game_patterns:
        cur.execute("""
            SELECT * FROM prompt_context
            WHERE game_id LIKE ?
            AND sport = 'NBA'
            ORDER BY source, created_at DESC
        """, (pattern,))
        
        results = cur.fetchall()
        if results:
            print(f"✅ Found {len(results)} records matching pattern: {pattern}")
            all_game_data.extend(results)
            break
    
    if not all_game_data:
        print("❌ No data found for this game!")
        print("\nLet me check what NBA games are in the database...")
        
        cur.execute("""
            SELECT DISTINCT game_id, match_date
            FROM prompt_context
            WHERE sport = 'NBA'
            AND match_date >= date('now')
            ORDER BY match_date
            LIMIT 10
        """)
        
        games = cur.fetchall()
        print(f"\nFound {len(games)} upcoming NBA games:")
        for game in games:
            print(f"  - {game['game_id']} ({game['match_date']})")
        
        conn.close()
        return
    
    # Group by source
    by_source = {}
    for row in all_game_data:
        source = row['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(row)
    
    print("\n2. DATA BY SOURCE")
    print("-" * 80)
    
    for source, records in sorted(by_source.items()):
        print(f"\n📊 {source.upper()} ({len(records)} records)")
        print("-" * 40)
        
        for i, record in enumerate(records, 1):
            data = json.loads(record['data'])
            print(f"\n  Record {i}:")
            print(f"    Context Type: {record['context_type']}")
            print(f"    Game ID: {record['game_id']}")
            print(f"    Match Date: {record['match_date']}")
            print(f"    Team Pick: {record['team_pick']}")
            print(f"    Created: {record['created_at']}")
            print(f"    Data: {json.dumps(data, indent=6)}")
    
    # Check for totals specifically
    print("\n3. TOTALS ANALYSIS")
    print("-" * 80)
    
    totals_data = []
    for row in all_game_data:
        data = json.loads(row['data'])
        market = data.get('market', '').lower()
        
        # Check various ways totals might be stored
        if market in ['total', 'totals', 'over/under', 'ou']:
            totals_data.append({
                'source': row['source'],
                'data': data,
                'created_at': row['created_at']
            })
        
        # Also check if direction field indicates a total
        if 'direction' in data and data['direction'] in ['over', 'under']:
            if {'source': row['source'], 'data': data, 'created_at': row['created_at']} not in totals_data:
                totals_data.append({
                    'source': row['source'],
                    'data': data,
                    'created_at': row['created_at']
                })
    
    if totals_data:
        print(f"Found {len(totals_data)} total picks:")
        for item in totals_data:
            data = item['data']
            direction = data.get('direction', data.get('pick', 'N/A'))
            line = data.get('line', 'N/A')
            print(f"\n  {item['source']}:")
            print(f"    Direction: {direction}")
            print(f"    Line: {line}")
            print(f"    Full data: {json.dumps(data, indent=6)}")
    else:
        print("❌ No totals data found!")
        print("\nThis could explain why the AI pick is incorrect.")
    
    # Check the AI pick itself
    print("\n4. AI PICK FROM DATABASE")
    print("-" * 80)
    
    cur.execute("""
        SELECT * FROM ai_picks
        WHERE game LIKE '%Memphis%Wizards%'
        OR game LIKE '%Grizzlies%Wizards%'
        ORDER BY id DESC
        LIMIT 1
    """)
    
    ai_pick = cur.fetchone()
    if ai_pick:
        print(f"Pick: {ai_pick['pick']}")
        print(f"Market: {ai_pick['market']}")
        print(f"Line: {ai_pick['line']}")
        print(f"Confidence: {ai_pick['confidence']}")
        print(f"Reasoning: {ai_pick['reasoning']}")
    else:
        print("❌ AI pick not found in database")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    
    # Analyze what we found
    sources_found = list(by_source.keys())
    print(f"\nSources with data: {', '.join(sources_found)}")
    
    if 'oddsshark' not in sources_found:
        print("⚠️  WARNING: OddsShark data missing")
    if 'oddstrader' not in sources_found:
        print("⚠️  WARNING: OddsTrader data missing (expected - scraper disabled)")
    if 'cbs_sports' not in sources_found:
        print("⚠️  WARNING: CBS Sports data missing")
    if 'kalshi' not in sources_found:
        print("⚠️  WARNING: Kalshi data missing")
    
    if not totals_data:
        print("\n❌ CRITICAL: No totals data found from any source!")
        print("   This means the AI had no consensus data for totals.")
        print("   The 5-star rating is likely based on incorrect or missing data.")
    else:
        print(f"\n✅ Found {len(totals_data)} totals picks")
        # Check if they agree
        directions = [item['data'].get('direction', item['data'].get('pick', '')) for item in totals_data]
        if len(set(directions)) > 1:
            print(f"   ⚠️  CONFLICT: Sources disagree on direction: {directions}")
        else:
            print(f"   All sources agree on: {directions[0]}")

if __name__ == "__main__":
    main()

