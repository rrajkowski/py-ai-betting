#!/usr/bin/env python3
"""
Test grading the imported NHL picks against actual game results.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.ai_picks import fetch_scores, _check_pick_result
from app.db import get_db, update_pick_result


def grade_nhl_picks():
    """Grade all pending NHL picks."""
    
    print("\n" + "="*60)
    print("GRADING NHL PICKS")
    print("="*60)
    
    # Fetch NHL scores
    print("\n📡 Fetching NHL scores from API...")
    try:
        scores = fetch_scores(sport="icehockey_nhl", days_from=3)
        print(f"✅ Found {len(scores)} NHL games")
    except Exception as e:
        print(f"❌ Error fetching scores: {e}")
        return
    
    # Build game score map
    game_score_map = {}
    for game in scores:
        if game.get('completed', False):
            game_id = f"{game.get('away_team')} @ {game.get('home_team')}"
            home_score = next((s['score'] for s in game.get('scores', []) if s['name'] == game['home_team']), None)
            away_score = next((s['score'] for s in game.get('scores', []) if s['name'] == game['away_team']), None)
            
            if home_score is not None and away_score is not None:
                game_score_map[game_id] = {
                    'home': int(home_score),
                    'away': int(away_score),
                    'date': game.get('commence_time', '')[:10]
                }
    
    print(f"✅ Found {len(game_score_map)} completed games")
    
    # Get pending NHL picks
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, game, pick, market, line, date 
        FROM ai_picks 
        WHERE sport = 'NHL' AND result = 'Pending'
        ORDER BY date
    """)
    pending_picks = cur.fetchall()
    
    print(f"\n🔍 Found {len(pending_picks)} pending NHL picks")
    print("="*60)
    
    graded = 0
    not_completed = 0
    
    for pick_id, game, pick, market, line, date in pending_picks:
        pick_date = date[:10] if date else ''
        
        print(f"\n📋 Pick #{pick_id}: {game}")
        print(f"   Pick: {pick} ({market})")
        if line:
            print(f"   Line: {line}")
        print(f"   Date: {pick_date}")
        
        if game in game_score_map:
            scores = game_score_map[game]
            
            # Check if dates match
            if scores['date'] != pick_date:
                print(f"   ⚠️  Date mismatch: Game {scores['date']} vs Pick {pick_date}")
                not_completed += 1
                continue
            
            print(f"   Score: {scores['away']}-{scores['home']}")
            
            # Grade the pick
            pick_dict = {
                'game': game,
                'pick': pick,
                'market': market,
                'line': line
            }
            
            result = _check_pick_result(pick_dict, scores['home'], scores['away'])
            print(f"   Result: {result}")
            
            if result != 'Pending':
                update_pick_result(pick_id, result)
                graded += 1
                print("   ✅ Updated in database")
            else:
                print("   ⚠️  Could not determine result")
                not_completed += 1
        else:
            print("   ⏳ Game not completed yet")
            not_completed += 1
    
    conn.close()
    
    print("\n" + "="*60)
    print("GRADING COMPLETE")
    print("="*60)
    print(f"✅ Graded: {graded} picks")
    print(f"⏳ Not completed: {not_completed} picks")
    
    # Show final results
    if graded > 0:
        print("\n📊 Final Results:")
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT game, pick, market, result, confidence 
            FROM ai_picks 
            WHERE sport = 'NHL' AND result != 'Pending'
            ORDER BY date
        """)
        for game, pick, market, result, confidence in cur.fetchall():
            emoji = "✅" if result == "Win" else "❌" if result == "Loss" else "➖"
            print(f"   {emoji} {game}")
            print(f"      Pick: {pick} ({market}) - {'⭐' * int(confidence)}")
            print(f"      Result: {result}")
        conn.close()


if __name__ == "__main__":
    grade_nhl_picks()

