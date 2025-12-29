#!/usr/bin/env python3
"""
Test the new market-based filtering logic.
"""

import sys
sys.path.insert(0, '.')
from app.ai_picks import fetch_odds


def test_market_filtering(sport_key, sport_name):
    """Test market filtering for a sport."""
    
    print(f"\n{'='*60}")
    print(f"{sport_name.upper()} MARKET FILTERING TEST")
    print(f"{'='*60}")
    
    raw_odds = fetch_odds(sport_key)
    print(f"\n📡 Found {len(raw_odds)} games from API")
    
    if not raw_odds:
        print("❌ No games available")
        return
    
    # Apply the new filtering logic
    normalized_odds = []
    total_markets = 0
    filtered_markets = 0
    
    for row in raw_odds:
        bookmaker = next((b for b in row.get("bookmakers", [])
                         if b["key"] == "draftkings"), None)
        if not bookmaker:
            continue
        
        game_name = f"{row['away_team']} @ {row['home_team']}"
        
        for market in bookmaker.get("markets", []):
            market_key = market["key"]
            outcomes = market.get("outcomes", [])
            
            # Count total markets
            total_markets += len(outcomes)
            
            # For h2h (moneyline), filter out extreme odds
            if market_key == "h2h":
                # Only include if BOTH sides have acceptable odds
                if len(outcomes) == 2:
                    odds1 = outcomes[0].get("price", 0)
                    odds2 = outcomes[1].get("price", 0)
                    
                    # Skip if either side is outside -150 to +150 range
                    if odds1 < -150 or odds1 > 150 or odds2 < -150 or odds2 > 150:
                        print(f"   ❌ Filtered h2h: {game_name} ({odds1}/{odds2})")
                        continue  # Skip this h2h market
                    else:
                        print(f"   ✅ Included h2h: {game_name} ({odds1}/{odds2})")
            
            # Include all spreads and totals
            for outcome in outcomes:
                normalized_odds.append({
                    "game": game_name,
                    "market": market_key,
                    "pick": outcome.get("name"),
                    "odds": outcome.get("price"),
                    "line": outcome.get("point")
                })
                filtered_markets += 1
    
    print("\n📊 Results:")
    print(f"   Total markets: {total_markets}")
    print(f"   Filtered markets: {filtered_markets}")
    print(f"   Filtered out: {total_markets - filtered_markets}")
    
    # Count by market type
    h2h_count = sum(1 for m in normalized_odds if m['market'] == 'h2h')
    spreads_count = sum(1 for m in normalized_odds if m['market'] == 'spreads')
    totals_count = sum(1 for m in normalized_odds if m['market'] == 'totals')
    
    print("\n📈 Market breakdown:")
    print(f"   h2h (moneyline): {h2h_count}")
    print(f"   spreads: {spreads_count}")
    print(f"   totals: {totals_count}")
    
    # Show sample markets
    print("\n📋 Sample markets (first 10):")
    for i, market in enumerate(normalized_odds[:10]):
        print(f"   {i+1}. {market['game']}")
        print(f"      {market['market']}: {market['pick']} @ {market['odds']}")
        if market['line']:
            print(f"      Line: {market['line']}")


if __name__ == "__main__":
    # Test NBA
    test_market_filtering("basketball_nba", "NBA")
    
    # Test NCAAB
    test_market_filtering("basketball_ncaab", "NCAAB")

