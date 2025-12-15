#!/usr/bin/env python3
"""
Test script to debug why Miami @ Pittsburgh isn't generating picks.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timezone
from app.utils.context_builder import create_super_prompt_payload
from app.ai_picks import fetch_odds
import json


def main():
    print("\n" + "="*80)
    print("MIAMI @ PITTSBURGH PICK GENERATION DEBUG")
    print("="*80)
    
    # Get target date
    now_utc = datetime.now(timezone.utc)
    target_date = now_utc.strftime('%Y-%m-%d')
    
    print(f"\n📅 Target Date: {target_date}")
    
    # 1. Check consensus data
    print(f"\n🔨 Building context payload for NFL...")
    context = create_super_prompt_payload(target_date, "americanfootball_nfl")
    
    games = context.get('games', [])
    
    if not games:
        print(f"   ❌ No games in context!")
        return
    
    print(f"   ✅ Found {len(games)} games in context")
    
    # Find Miami @ Pittsburgh
    miami_pitt = None
    for game in games:
        game_id = game.get('game_id', '')
        if 'Miami' in game_id and 'Pittsburgh' in game_id:
            miami_pitt = game
            break
    
    if not miami_pitt:
        print(f"\n   ❌ Miami @ Pittsburgh not found in context!")
        print(f"\n   Available games:")
        for g in games:
            print(f"      - {g.get('game_id')}")
        return
    
    print(f"\n✅ Found Miami @ Pittsburgh in context:")
    print(f"   Game ID: {miami_pitt.get('game_id')}")
    print(f"   Match Date: {miami_pitt.get('match_date')}")
    
    expert_consensus = miami_pitt.get('context', {}).get('expert_consensus', [])
    print(f"   Expert Consensus Count: {len(expert_consensus)}")
    
    if expert_consensus:
        print(f"\n   📊 Expert Consensus Data:")
        for i, consensus in enumerate(expert_consensus, 1):
            print(f"      {i}. Source: {consensus.get('source', 'unknown')}")
            print(f"         Market: {consensus.get('market', 'N/A')}")
            print(f"         Line: {consensus.get('line', 'N/A')}")
            print(f"         Odds: {consensus.get('odds_american', consensus.get('odds', 'N/A'))}")
            print(f"         Star Rating: {consensus.get('star_rating', 'N/A')}")
            print(f"         Confidence: {consensus.get('confidence', 'N/A')}")
    
    # 2. Check odds data
    print(f"\n🎲 Fetching odds for NFL...")
    raw_odds = fetch_odds("americanfootball_nfl")
    
    if not raw_odds:
        print(f"   ❌ No odds data!")
        return
    
    print(f"   ✅ Found {len(raw_odds)} games with odds")
    
    # Find Miami @ Pittsburgh in odds
    miami_pitt_odds = None
    for game in raw_odds:
        home = game.get('home_team', '')
        away = game.get('away_team', '')
        if ('Miami' in home or 'Miami' in away) and ('Pittsburgh' in home or 'Pittsburgh' in away):
            miami_pitt_odds = game
            break
    
    if not miami_pitt_odds:
        print(f"\n   ❌ Miami @ Pittsburgh not found in odds!")
        print(f"\n   Available games:")
        for g in raw_odds[:5]:
            print(f"      - {g.get('away_team')} @ {g.get('home_team')}")
        return
    
    print(f"\n✅ Found Miami @ Pittsburgh in odds:")
    print(f"   {miami_pitt_odds.get('away_team')} @ {miami_pitt_odds.get('home_team')}")
    print(f"   Commence Time: {miami_pitt_odds.get('commence_time')}")
    
    # Show markets
    bookmakers = miami_pitt_odds.get('bookmakers', [])
    if bookmakers:
        dk = next((b for b in bookmakers if b.get('key') == 'draftkings'), None)
        if dk:
            markets = dk.get('markets', [])
            print(f"\n   📊 DraftKings Markets ({len(markets)} total):")
            for market in markets:
                market_key = market.get('key')
                outcomes = market.get('outcomes', [])
                print(f"\n      {market_key}:")
                for outcome in outcomes:
                    print(f"         {outcome.get('name')}: {outcome.get('price')} (line: {outcome.get('point', 'N/A')})")
    
    print("\n" + "="*80)
    print("DIAGNOSIS:")
    print("="*80)
    
    if expert_consensus:
        valid_picks = [c for c in expert_consensus if c.get('market') in ['spread', 'totals', 'total']]
        extreme_ml = [c for c in expert_consensus if c.get('market') == 'moneyline' and abs(c.get('odds_american', 0)) > 150]
        
        print(f"✅ Expert consensus data exists: {len(expert_consensus)} picks")
        print(f"   - Valid picks (spread/total): {len(valid_picks)}")
        print(f"   - Extreme moneyline picks (rejected): {len(extreme_ml)}")
        
        if valid_picks:
            print(f"\n✅ AI should be able to generate picks from:")
            for pick in valid_picks:
                print(f"   - {pick.get('source')}: {pick.get('market')} {pick.get('line')} @ {pick.get('odds', pick.get('odds_american'))}")
        else:
            print(f"\n❌ No valid picks within odds range (-150 to +150)")
    else:
        print(f"❌ No expert consensus data - AI cannot generate picks")


if __name__ == "__main__":
    main()

