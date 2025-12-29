"""Check what data is actually in the prompt_context table."""

import sqlite3
import json
from datetime import datetime, timedelta

DB_PATH = "bets.db"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 80)
print("PROMPT CONTEXT DATA ANALYSIS")
print("=" * 80)

# Get date range for recent data
today = datetime.now().date()
yesterday = today - timedelta(days=1)
tomorrow = today + timedelta(days=1)

# Query recent context data
cur.execute("""
    SELECT context_type, sport, source, data, match_date
    FROM prompt_context
    WHERE match_date >= ?
    ORDER BY sport, context_type, match_date
""", (str(yesterday),))

rows = cur.fetchall()

print(f"\n📊 Total context entries: {len(rows)}")

# Group by sport and source
by_sport = {}
by_source = {}
by_market = {}

for row in rows:
    sport = row['sport'] or 'UNKNOWN'
    source = row['source'] or 'UNKNOWN'
    context_type = row['context_type']

    # Count by sport
    if sport not in by_sport:
        by_sport[sport] = 0
    by_sport[sport] += 1

    # Count by source
    if source not in by_source:
        by_source[source] = 0
    by_source[source] += 1

    # Parse data to check market types
    try:
        data = json.loads(row['data'])
        market = data.get('market', 'UNKNOWN')

        if market not in by_market:
            by_market[market] = {'total': 0, 'by_source': {}}

        by_market[market]['total'] += 1

        if source not in by_market[market]['by_source']:
            by_market[market]['by_source'][source] = 0
        by_market[market]['by_source'][source] += 1
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

print("\n📊 BY SPORT:")
print("-" * 80)
for sport, count in sorted(by_sport.items()):
    print(f"  {sport:15s}: {count:3d} entries")

print("\n📊 BY SOURCE:")
print("-" * 80)
for source, count in sorted(by_source.items()):
    print(f"  {source:20s}: {count:3d} entries")

print("\n📊 BY MARKET TYPE:")
print("-" * 80)
for market, data in sorted(by_market.items()):
    print(f"\n  {market.upper()}:")
    print(f"    Total: {data['total']} entries")
    print("    By source:")
    for source, count in sorted(data['by_source'].items()):
        pct = (count / data['total']) * 100
        print(f"      {source:20s}: {count:3d} ({pct:5.1f}%)")

# Sample some entries to see what they look like
print("\n\n📋 SAMPLE ENTRIES (First 5):")
print("-" * 80)

cur.execute("""
    SELECT context_type, sport, source, data, match_date
    FROM prompt_context
    WHERE match_date >= ?
    ORDER BY match_date
    LIMIT 5
""", (str(yesterday),))

samples = cur.fetchall()
for i, row in enumerate(samples, 1):
    print(f"\n{i}. {row['sport']} - {row['source']} - {row['context_type']}")
    print(f"   Date: {row['match_date']}")
    try:
        data = json.loads(row['data'])
        print(f"   Market: {data.get('market', 'N/A')}")
        print(f"   Line: {data.get('line', 'N/A')}")
        print(f"   Data: {json.dumps(data, indent=6)[:200]}...")
    except (json.JSONDecodeError, KeyError, TypeError):
        print(f"   Data: {row['data'][:100]}...")

conn.close()

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)

# Calculate market distribution
total_market_entries = sum(data['total'] for data in by_market.values())
if total_market_entries > 0:
    print("\n📊 MARKET DISTRIBUTION:")
    for market, data in sorted(by_market.items(), key=lambda x: x[1]['total'], reverse=True):
        pct = (data['total'] / total_market_entries) * 100
        print(f"  {market:15s}: {data['total']:3d} entries ({pct:5.1f}%)")

    # Check for bias
    totals_pct = (by_market.get('total', {}).get(
        'total', 0) / total_market_entries) * 100
    spread_pct = (by_market.get('spread', {}).get(
        'total', 0) / total_market_entries) * 100
    ml_pct = (by_market.get('moneyline', {}).get(
        'total', 0) / total_market_entries) * 100

    print("\n🔍 ANALYSIS:")
    if totals_pct > 50:
        print(
            f"  ⚠️  TOTALS BIAS: {totals_pct:.0f}% of scraped data is totals")
        print("      This explains why AI picks are mostly totals!")

    if spread_pct < 20:
        print(
            f"  ⚠️  LOW SPREADS: Only {spread_pct:.0f}% of scraped data is spreads")
        print("      Scrapers may not be collecting spread data properly")

    if ml_pct < 20:
        print(
            f"  ⚠️  LOW MONEYLINE: Only {ml_pct:.0f}% of scraped data is moneyline")
        print("      Scrapers may not be collecting moneyline data properly")

print("\n" + "=" * 80)
