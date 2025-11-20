"""Test the fixed OddsShark scraper."""

import json
import sqlite3
from app.utils.scraper import scrape_oddsshark_consensus
from datetime import datetime
import sys
import os

# Add parent directory to path FIRST
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


print("=" * 80)
print("TESTING FIXED ODDSSHARK SCRAPER")
print("=" * 80)

# Test with NFL
sport = "americanfootball_nfl"
target_date = datetime.now().strftime("%Y-%m-%d")
print(f"\n🏈 Testing {sport.upper()} for {target_date}...")

# Clear old data first

conn = sqlite3.connect("bets.db")
cur = conn.cursor()

# Sport name in DB is uppercase (e.g., "NFL" not "americanfootball_nfl")
sport_upper = sport.split('_')[-1].upper()

cur.execute(
    "DELETE FROM prompt_context WHERE source = 'oddsshark' AND sport = ?", (sport_upper,))
conn.commit()
print(f"🗑️  Cleared old OddsShark data for {sport_upper}")

# Run scraper
scrape_oddsshark_consensus(target_date, sport)

# Query database to see what was stored
cur.execute("""
    SELECT context_type, sport, source, data, match_date
    FROM prompt_context
    WHERE source = 'oddsshark' AND sport = ?
    ORDER BY match_date
""", (sport_upper,))

results = cur.fetchall()
conn.close()

print(f"\n✅ Scraped {len(results)} total picks\n")

# Count by market
by_market = {}
for row in results:
    data = json.loads(row[3])  # row[3] is the 'data' column
    market = data.get('market', 'UNKNOWN')
    if market not in by_market:
        by_market[market] = []
    by_market[market].append(row)

print("📊 MARKET DISTRIBUTION:")
print("-" * 80)
for market, picks in sorted(by_market.items()):
    pct = (len(picks) / len(results)) * 100 if results else 0
    print(f"  {market:15s}: {len(picks):3d} picks ({pct:5.1f}%)")

print("\n📋 SAMPLE PICKS (first 3 from each market):")
print("-" * 80)

for market in ['moneyline', 'spread', 'total']:
    if market in by_market:
        print(f"\n{market.upper()}:")
        for i, row in enumerate(by_market[market][:3], 1):
            data = json.loads(row[3])  # row[3] is the 'data' column
            print(f"  {i}. Sport: {row[1]}, Date: {row[4]}")
            print(f"     Market: {data.get('market', 'N/A')}")
            print(f"     Line: {data.get('line', 'N/A')}")
            print(f"     Odds: {data.get('odds_american', 'N/A')}")
            if 'team' in data:
                print(f"     Team: {data.get('team', 'N/A')}")

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)

if len(by_market.get('moneyline', [])) > 0:
    print("✅ Moneyline picks are being collected!")
else:
    print("❌ Moneyline picks are NOT being collected")

if len(by_market.get('spread', [])) > 0:
    print("✅ Spread picks are being collected!")
else:
    print("❌ Spread picks are NOT being collected")

if len(by_market.get('total', [])) > 0:
    print("✅ Total picks are being collected!")
else:
    print("❌ Total picks are NOT being collected")

# Check balance
total_count = len(results)
if total_count > 0:
    ml_pct = (len(by_market.get('moneyline', [])) / total_count) * 100
    spread_pct = (len(by_market.get('spread', [])) / total_count) * 100
    total_pct = (len(by_market.get('total', [])) / total_count) * 100

    print(f"\n📊 BALANCE CHECK:")
    print(f"   Moneyline: {ml_pct:.0f}% (target: ~33%)")
    print(f"   Spread:    {spread_pct:.0f}% (target: ~33%)")
    print(f"   Total:     {total_pct:.0f}% (target: ~33%)")

    if ml_pct > 20 and spread_pct > 20 and total_pct > 20:
        print("\n✅ GOOD BALANCE - All markets represented!")
    else:
        print("\n⚠️ IMBALANCED - Some markets underrepresented")

print("\n" + "=" * 80)
