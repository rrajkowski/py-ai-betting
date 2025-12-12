#!/usr/bin/env python3
"""
Debug script to check the exact structure of NFL context data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from app.utils.context_builder import create_super_prompt_payload
import json


def main():
    print("\n" + "="*80)
    print("NFL CONTEXT STRUCTURE DEBUG")
    print("="*80)
    
    # Get target date
    now_utc = datetime.now(timezone.utc)
    target_date = now_utc.strftime('%Y-%m-%d')
    
    print(f"\n📅 Target Date: {target_date}")
    
    # Build context payload
    print(f"\n🔨 Building context payload for NFL...")
    context = create_super_prompt_payload(target_date, "americanfootball_nfl")
    
    games = context.get('games', [])
    
    if not games:
        print(f"   ❌ No games in context!")
        return
    
    print(f"   ✅ Found {len(games)} games in context")
    
    # Show structure of first game
    print(f"\n📋 Structure of first game:")
    print("="*80)
    first_game = games[0]
    print(json.dumps(first_game, indent=2))
    
    # Check for expert consensus
    print(f"\n🔍 Checking for expert consensus in all games:")
    print("="*80)
    for i, game in enumerate(games, 1):
        game_id = game.get('game_id', 'unknown')
        expert_consensus = game.get('context', {}).get('expert_consensus', [])
        
        print(f"\n{i}. Game ID: {game_id}")
        print(f"   Match Date: {game.get('match_date')}")
        print(f"   Expert Consensus Count: {len(expert_consensus)}")
        
        if expert_consensus:
            print(f"   Expert Consensus Data:")
            for j, consensus in enumerate(expert_consensus, 1):
                print(f"      {j}. Source: {consensus.get('source', 'unknown')}")
                print(f"         Pick: {consensus.get('pick', 'N/A')}")
                print(f"         Confidence: {consensus.get('confidence', 'N/A')}")
                print(f"         Full data: {json.dumps(consensus, indent=10)[:200]}...")
        else:
            print(f"   ⚠️  NO EXPERT CONSENSUS DATA!")
    
    print("\n" + "="*80)
    print("DIAGNOSIS:")
    print("="*80)
    
    games_with_consensus = sum(1 for g in games if g.get('context', {}).get('expert_consensus', []))
    
    if games_with_consensus == 0:
        print("❌ NO GAMES HAVE EXPERT CONSENSUS DATA")
        print("\nPossible reasons:")
        print("1. Scrapers stored data with different game_id format")
        print("2. Context builder is not properly attaching consensus to games")
        print("3. Consensus data is in database but filtered out by date range")
    else:
        print(f"✅ {games_with_consensus}/{len(games)} games have expert consensus data")


if __name__ == "__main__":
    main()

