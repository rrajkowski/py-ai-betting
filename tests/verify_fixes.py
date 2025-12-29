#!/usr/bin/env python3
"""Verify all scraper and Kalshi API fixes are working correctly."""

from datetime import datetime
from collections import defaultdict
from app.utils.db import get_db
from app.utils.context_builder import build_merged_context

print("=" * 80)
print("VERIFICATION REPORT - Scrapers & Kalshi API")
print("=" * 80)

conn = get_db()
cur = conn.cursor()

# 1. Check data sources
print("\n1. DATA SOURCES")
print("-" * 80)

cur.execute("""
    SELECT source, COUNT(*) as count, COUNT(DISTINCT game_id) as games
    FROM prompt_context
    WHERE sport = 'NBA'
    GROUP BY source
    ORDER BY source
""")

sources = cur.fetchall()
for source, count, games in sources:
    status = "✅" if count > 0 else "❌"
    print(f"{status} {source:15s} {count:3d} records, {games:2d} games")

# 2. Check game_id matching
print("\n2. GAME ID MATCHING")
print("-" * 80)

cur.execute("""
    SELECT game_id, source, COUNT(*) as count
    FROM prompt_context
    WHERE sport = 'NBA'
    GROUP BY game_id, source
    ORDER BY game_id
""")

results = cur.fetchall()
games = defaultdict(lambda: defaultdict(int))
for game_id, source, count in results:
    games[game_id][source] = count

multi_source = sum(1 for sources in games.values() if len(sources) >= 2)
three_source = sum(1 for sources in games.values() if len(sources) >= 3)

print(f"Total unique games: {len(games)}")
print(f"Games with 2+ sources: {multi_source} ✅")
print(f"Games with 3+ sources: {three_source}")

# 3. Show multi-source games
print("\n3. MULTI-SOURCE GAMES (Should get 4-5 star picks)")
print("-" * 80)

for game_id, sources in sorted(games.items()):
    if len(sources) >= 2:
        source_list = ", ".join(sources.keys())
        stars = 3 + (len(sources) - 1)
        print(f"⭐ {stars} stars: {game_id}")
        print(f"   Sources: {source_list}")

# 4. Check Kalshi data
print("\n4. KALSHI API STATUS")
print("-" * 80)

cur.execute("""
    SELECT COUNT(*) as count, COUNT(DISTINCT game_id) as games
    FROM prompt_context
    WHERE sport = 'NBA' AND source = 'kalshi'
""")

kalshi_count, kalshi_games = cur.fetchone()
status = "✅ WORKING" if kalshi_count > 0 else "❌ NOT WORKING"
print(f"{status} - {kalshi_count} markets for {kalshi_games} games")

# 5. Check date consistency
print("\n5. DATE CONSISTENCY")
print("-" * 80)

cur.execute("""
    SELECT DISTINCT match_date
    FROM prompt_context
    WHERE sport = 'NBA'
    ORDER BY match_date
    LIMIT 5
""")

dates = [row[0] for row in cur.fetchall()]
print("Game dates in database:")
for date in dates:
    print(f"  • {date}")

# 6. Context builder test
print("\n6. CONTEXT BUILDER TEST")
print("-" * 80)


target_date = datetime.now().strftime('%Y-%m-%d')
context_games = build_merged_context(target_date, 'NBA')

games_with_multiple_sources = sum(
    1 for game in context_games
    if len(game.get('context', {}).get('expert_consensus', [])) > 0
    and len(set(expert.get('source') for expert in game.get('context', {}).get('expert_consensus', []))) >= 2
)

print(f"✅ Context builder merged {len(context_games)} games")
print(f"✅ {games_with_multiple_sources} games have multiple expert sources")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

all_working = (
    kalshi_count > 0 and
    multi_source >= 2 and
    len(context_games) > 0
)

if all_working:
    print("✅ ALL SYSTEMS WORKING!")
    print(f"   • Kalshi API: {kalshi_count} markets")
    print(f"   • Game ID matching: {multi_source} games with 2+ sources")
    print(f"   • Context builder: {len(context_games)} games merged")
    print("\n🎯 Ready for AI picks generation with 4-5 star ratings!")
else:
    print("⚠️  SOME ISSUES DETECTED")
    if kalshi_count == 0:
        print("   • Kalshi API not returning data")
    if multi_source < 2:
        print("   • Game ID matching not working")
    if len(context_games) == 0:
        print("   • Context builder not merging data")

conn.close()
