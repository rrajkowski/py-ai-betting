#!/usr/bin/env python3
"""
Comprehensive test script to verify all scrapers and Kalshi API are working properly.
Tests: OddsShark, CBS, OddsTrader (disabled), Kalshi API, and context builder.
"""

from datetime import datetime
from app.utils.scraper import scrape_oddsshark_consensus, scrape_cbs_expert_picks
from app.utils.kalshi_api import fetch_kalshi_consensus
from app.utils.context_builder import create_super_prompt_payload
from app.utils.db import get_db
import json

def test_scrapers_and_api():
    """Test all data sources for NBA."""
    
    target_date = datetime.now().strftime('%Y-%m-%d')
    sport_key = 'basketball_nba'
    sport_name = 'NBA'
    
    print("=" * 80)
    print(f"TESTING ALL DATA SOURCES FOR {sport_name} - {target_date}")
    print("=" * 80)
    
    # Clear existing data for clean test
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM prompt_context WHERE sport = ? AND match_date >= ?", (sport_name, target_date))
    conn.commit()
    print(f"\n🧹 Cleared existing {sport_name} context data for {target_date}")
    
    # Test 1: OddsShark
    print("\n" + "=" * 80)
    print("TEST 1: OddsShark Scraper")
    print("=" * 80)
    scrape_oddsshark_consensus(target_date, sport_key)
    
    # Check what was stored
    cur.execute("""
        SELECT game_id, team_pick, data, source 
        FROM prompt_context 
        WHERE sport = ? AND source = 'oddsshark'
        ORDER BY game_id
    """, (sport_name,))
    oddsshark_results = cur.fetchall()
    print(f"\n✅ OddsShark: Stored {len(oddsshark_results)} picks")
    if oddsshark_results:
        print(f"   Sample: {oddsshark_results[0]['game_id']} - {oddsshark_results[0]['team_pick']}")
        print(f"   Data: {json.loads(oddsshark_results[0]['data'])}")
    
    # Test 2: CBS Sports
    print("\n" + "=" * 80)
    print("TEST 2: CBS Sports Scraper")
    print("=" * 80)
    scrape_cbs_expert_picks(target_date, sport_key)
    
    cur.execute("""
        SELECT game_id, team_pick, data, source 
        FROM prompt_context 
        WHERE sport = ? AND source = 'cbs_sports'
        ORDER BY game_id
    """, (sport_name,))
    cbs_results = cur.fetchall()
    print(f"\n✅ CBS Sports: Stored {len(cbs_results)} picks")
    if cbs_results:
        print(f"   Sample: {cbs_results[0]['game_id']} - {cbs_results[0]['team_pick']}")
        print(f"   Data: {json.loads(cbs_results[0]['data'])}")
    
    # Test 3: Kalshi API
    print("\n" + "=" * 80)
    print("TEST 3: Kalshi API")
    print("=" * 80)
    fetch_kalshi_consensus(sport_key, target_date)
    
    cur.execute("""
        SELECT game_id, data, source 
        FROM prompt_context 
        WHERE sport = ? AND source = 'kalshi'
        ORDER BY game_id
    """, (sport_name,))
    kalshi_results = cur.fetchall()
    print(f"\n✅ Kalshi: Stored {len(kalshi_results)} markets")
    if kalshi_results:
        print(f"   Sample: {kalshi_results[0]['game_id']}")
        kalshi_data = json.loads(kalshi_results[0]['data'])
        print(f"   Data: {kalshi_data}")
    
    # Test 4: Context Builder
    print("\n" + "=" * 80)
    print("TEST 4: Context Builder")
    print("=" * 80)
    context_payload = create_super_prompt_payload(target_date, sport_name)
    
    games = context_payload.get('games', [])
    print(f"\n✅ Context Builder: Built context for {len(games)} games")
    
    if games:
        # Analyze first game in detail
        game = games[0]
        print(f"\n📊 Sample Game: {game['game_id']}")
        print(f"   Match Date: {game['match_date']}")
        
        expert_consensus = game['context'].get('expert_consensus', [])
        public_consensus = game['context'].get('public_consensus', {})
        
        print(f"\n   Expert Consensus Sources: {len(expert_consensus)}")
        for i, expert in enumerate(expert_consensus, 1):
            source = expert.get('source', 'unknown')
            print(f"      {i}. {source}: {expert}")
        
        print(f"\n   Public Consensus (Kalshi): {bool(public_consensus)}")
        if public_consensus:
            print(f"      {public_consensus}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"OddsShark picks:  {len(oddsshark_results)}")
    print(f"CBS picks:        {len(cbs_results)}")
    print(f"Kalshi markets:   {len(kalshi_results)}")
    print(f"Games with data:  {len(games)}")
    
    # Check for games with multiple sources
    if games:
        multi_source_games = 0
        for game in games:
            expert_count = len(game['context'].get('expert_consensus', []))
            has_kalshi = bool(game['context'].get('public_consensus', {}))
            total_sources = expert_count + (1 if has_kalshi else 0)
            if total_sources >= 2:
                multi_source_games += 1
        
        print(f"\nGames with 2+ sources: {multi_source_games}/{len(games)}")
        print(f"Expected 4-5 star picks: {multi_source_games} (if consensus agrees)")
    
    conn.close()

if __name__ == "__main__":
    test_scrapers_and_api()

