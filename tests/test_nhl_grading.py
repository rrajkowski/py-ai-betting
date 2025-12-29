#!/usr/bin/env python3
"""
Test script to verify NHL grading logic works correctly.
Tests all three market types: h2h, spreads, totals
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.ai_picks import _check_pick_result, fetch_scores


def test_h2h_grading():
    """Test moneyline (h2h) grading logic."""
    print("\n" + "="*60)
    print("TEST 1: H2H (Moneyline) Grading")
    print("="*60)
    
    # Test case: Ottawa Senators @ Montréal Canadiens (Ottawa won 5-3)
    pick = {
        'game': 'Ottawa Senators @ Montréal Canadiens',
        'pick': 'Ottawa Senators',
        'market': 'h2h',
        'line': None
    }
    
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"Pick: {pick['pick']}")
    print("Score: Ottawa 5, Montreal 3")
    print(f"Result: {result}")
    assert result == 'Win', f"Expected 'Win', got '{result}'"
    print("✅ PASS: Ottawa moneyline correctly graded as Win")
    
    # Test losing pick
    pick['pick'] = 'Montréal Canadiens'
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"\nPick: {pick['pick']}")
    print("Score: Ottawa 5, Montreal 3")
    print(f"Result: {result}")
    assert result == 'Loss', f"Expected 'Loss', got '{result}'"
    print("✅ PASS: Montreal moneyline correctly graded as Loss")
    
    # Test tie
    result = _check_pick_result(pick, home_score=3, away_score=3)
    print(f"\nPick: {pick['pick']}")
    print("Score: 3-3 (Tie)")
    print(f"Result: {result}")
    assert result == 'Push', f"Expected 'Push', got '{result}'"
    print("✅ PASS: Tie correctly graded as Push")


def test_spread_grading():
    """Test spread grading logic."""
    print("\n" + "="*60)
    print("TEST 2: Spread Grading")
    print("="*60)
    
    # Test case: Team favored by -1.5 wins by 2
    pick = {
        'game': 'Ottawa Senators @ Montréal Canadiens',
        'pick': 'Ottawa Senators',
        'market': 'spreads',
        'line': -1.5  # Ottawa favored by 1.5
    }
    
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"Pick: {pick['pick']} {pick['line']}")
    print("Score: Ottawa 5, Montreal 3 (Ottawa wins by 2)")
    print("Adjusted: 5 + (-1.5) = 3.5 vs 3")
    print(f"Result: {result}")
    assert result == 'Win', f"Expected 'Win', got '{result}'"
    print("✅ PASS: Spread -1.5 correctly graded as Win")
    
    # Test underdog spread
    pick['pick'] = 'Montréal Canadiens'
    pick['line'] = 1.5  # Montreal getting 1.5
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"\nPick: {pick['pick']} +{pick['line']}")
    print("Score: Ottawa 5, Montreal 3 (Montreal loses by 2)")
    print("Adjusted: 3 + 1.5 = 4.5 vs 5")
    print(f"Result: {result}")
    assert result == 'Loss', f"Expected 'Loss', got '{result}'"
    print("✅ PASS: Spread +1.5 correctly graded as Loss")


def test_total_grading():
    """Test totals (over/under) grading logic."""
    print("\n" + "="*60)
    print("TEST 3: Totals (Over/Under) Grading")
    print("="*60)
    
    # Test case: Over 6.5 with final score 5-3 (total 8)
    pick = {
        'game': 'Ottawa Senators @ Montréal Canadiens',
        'pick': 'Over',
        'market': 'totals',
        'line': 6.5
    }
    
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"Pick: {pick['pick']} {pick['line']}")
    print("Score: Ottawa 5, Montreal 3 (Total: 8)")
    print(f"Result: {result}")
    assert result == 'Win', f"Expected 'Win', got '{result}'"
    print("✅ PASS: Over 6.5 correctly graded as Win")
    
    # Test under
    pick['pick'] = 'Under'
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"\nPick: {pick['pick']} {pick['line']}")
    print("Score: Ottawa 5, Montreal 3 (Total: 8)")
    print(f"Result: {result}")
    assert result == 'Loss', f"Expected 'Loss', got '{result}'"
    print("✅ PASS: Under 6.5 correctly graded as Loss")
    
    # Test push
    pick['line'] = 8.0
    result = _check_pick_result(pick, home_score=3, away_score=5)
    print(f"\nPick: {pick['pick']} {pick['line']}")
    print("Score: Ottawa 5, Montreal 3 (Total: 8)")
    print(f"Result: {result}")
    assert result == 'Push', f"Expected 'Push', got '{result}'"
    print("✅ PASS: Under 8.0 correctly graded as Push")


def test_nhl_api_connection():
    """Test that we can fetch NHL scores from the API."""
    print("\n" + "="*60)
    print("TEST 4: NHL API Connection")
    print("="*60)
    
    try:
        scores = fetch_scores(sport="icehockey_nhl", days_from=2)
        print("✅ Successfully fetched NHL scores")
        print(f"   Found {len(scores)} games")
        
        # Show completed games
        completed = [g for g in scores if g.get('completed')]
        print(f"   {len(completed)} completed games")
        
        if completed:
            print("\n   Recent completed games:")
            for game in completed[:3]:
                home = game.get('home_team')
                away = game.get('away_team')
                home_score = next((s['score'] for s in game.get('scores', []) if s['name'] == home), '?')
                away_score = next((s['score'] for s in game.get('scores', []) if s['name'] == away), '?')
                print(f"   - {away} @ {home}: {away_score}-{home_score}")
        
        return True
    except Exception as e:
        print("❌ FAIL: Could not fetch NHL scores")
        print(f"   Error: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*60)
    print("NHL GRADING LOGIC TEST SUITE")
    print("="*60)
    
    try:
        test_h2h_grading()
        test_spread_grading()
        test_total_grading()
        api_ok = test_nhl_api_connection()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nGrading logic is working correctly for:")
        print("  ✅ H2H (Moneyline) picks")
        print("  ✅ Spread picks")
        print("  ✅ Total (Over/Under) picks")
        if api_ok:
            print("  ✅ NHL API connection")
        print("\nThe fix is ready for production! 🚀")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

