"""Test duplicate and conflict detection logic."""

import sys
sys.path.insert(0, '/Users/rubenrajkowski/Sites/py-ai-betting')

from datetime import datetime, timezone, timedelta

# Simulate the duplicate detection logic
def test_duplicate_detection():
    """Test that duplicate detection catches conflicts."""
    
    # Simulate existing picks in database
    existing_picks = {
        ("Buffalo Bills @ Houston Texans", "totals", "Over", 43.5),
        ("Miami (OH) RedHawks @ Buffalo Bulls", "totals", "Under", 38.5),
    }
    
    existing_games = {
        "Buffalo Bills @ Houston Texans",
        "Miami (OH) RedHawks @ Buffalo Bulls",
    }
    
    # Simulate new picks from AI
    new_picks = [
        {
            "game": "Buffalo Bills @ Houston Texans",
            "market": "totals",
            "pick": "Under 43.5",
            "line": 43.5,
            "confidence": 3
        },
        {
            "game": "Miami (OH) RedHawks @ Buffalo Bulls",
            "market": "totals",
            "pick": "Under",
            "line": 38.5,
            "confidence": 4
        },
        {
            "game": "New Game @ Another Team",
            "market": "spread",
            "pick": "New Game -3.5",
            "line": -3.5,
            "confidence": 4
        }
    ]
    
    # Test duplicate detection
    unique_picks = []
    seen_games = set()
    skipped_duplicates = 0
    skipped_conflicts = 0
    
    for pick in new_picks:
        game = pick.get('game', '').strip()
        market = pick.get('market', '').strip()
        pick_value = pick.get('pick', '').strip()
        line = pick.get('line')
        
        # Check if this exact pick already exists in database
        pick_signature = (game, market, pick_value, line)
        if pick_signature in existing_picks:
            print(f"❌ DUPLICATE: {game} - {pick_value}")
            skipped_duplicates += 1
            continue
        
        # Check if this game already has a pick in database
        if game in existing_games:
            print(f"⚠️ CONFLICT: {game} already has a pick (trying to add {pick_value})")
            skipped_conflicts += 1
            continue
        
        # Check if we've already added a pick for this game in current batch
        if game in seen_games:
            print(f"⚠️ CONFLICT: {game} already in current batch")
            skipped_conflicts += 1
            continue
        
        print(f"✅ ALLOWED: {game} - {pick_value}")
        seen_games.add(game)
        unique_picks.append(pick)
    
    print(f"\n📊 Results:")
    print(f"   Total new picks: {len(new_picks)}")
    print(f"   Duplicates skipped: {skipped_duplicates}")
    print(f"   Conflicts skipped: {skipped_conflicts}")
    print(f"   Unique picks to save: {len(unique_picks)}")
    
    # Assertions
    assert skipped_duplicates == 1, "Should skip 1 exact duplicate"
    assert skipped_conflicts == 1, "Should skip 1 conflicting pick"
    assert len(unique_picks) == 1, "Should only allow 1 new pick"
    assert unique_picks[0]['game'] == "New Game @ Another Team", "Should allow new game"
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_duplicate_detection()

