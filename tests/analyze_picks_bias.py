"""Analyze the picks to identify bias patterns."""

import pandas as pd
import sys

# Read the CSV
csv_path = "2025-11-20T22-59_export.csv"

try:
    df = pd.read_csv(csv_path)
except FileNotFoundError:
    print(f"❌ File not found: {csv_path}")
    sys.exit(1)

print("=" * 80)
print("AI PICKS ANALYSIS - Bias Detection")
print("=" * 80)

# Basic stats
total_picks = len(df)
print(f"\n📊 Total Picks: {total_picks}")

# Market distribution
print("\n📈 MARKET DISTRIBUTION:")
print("-" * 80)
market_counts = df['market'].value_counts()
for market, count in market_counts.items():
    pct = (count / total_picks) * 100
    print(f"  {market:15s}: {count:2d} picks ({pct:5.1f}%)")

# For totals, analyze Over vs Under
totals_df = df[df['market'] == 'totals']
if len(totals_df) > 0:
    print("\n📊 TOTALS BREAKDOWN (Over vs Under):")
    print("-" * 80)
    
    # Count Over vs Under
    over_count = totals_df['pick'].str.contains('Over', case=False, na=False).sum()
    under_count = totals_df['pick'].str.contains('Under', case=False, na=False).sum()
    
    over_pct = (over_count / len(totals_df)) * 100
    under_pct = (under_count / len(totals_df)) * 100
    
    print(f"  Over:  {over_count:2d} picks ({over_pct:5.1f}%)")
    print(f"  Under: {under_count:2d} picks ({under_pct:5.1f}%)")
    
    if under_count > over_count * 2:
        print("\n  ⚠️  WARNING: Heavy Under bias detected!")
        print(f"      Under picks are {under_count/max(over_count, 1):.1f}x more common than Over picks")

# For spreads, analyze favorites vs underdogs
spreads_df = df[df['market'] == 'spreads']
if len(spreads_df) > 0:
    print("\n📊 SPREADS BREAKDOWN:")
    print("-" * 80)
    
    # Count by line (negative = favorite, positive = underdog)
    favorite_count = (spreads_df['line'] < 0).sum()
    underdog_count = (spreads_df['line'] > 0).sum()
    
    if favorite_count + underdog_count > 0:
        fav_pct = (favorite_count / (favorite_count + underdog_count)) * 100
        dog_pct = (underdog_count / (favorite_count + underdog_count)) * 100
        
        print(f"  Favorites: {favorite_count:2d} picks ({fav_pct:5.1f}%)")
        print(f"  Underdogs: {underdog_count:2d} picks ({dog_pct:5.1f}%)")

# H2H analysis
h2h_df = df[df['market'] == 'h2h']
if len(h2h_df) > 0:
    print("\n📊 H2H (MONEYLINE) BREAKDOWN:")
    print("-" * 80)
    
    # Count by odds (negative = favorite, positive = underdog)
    favorite_count = (h2h_df['odds_american'] < 0).sum()
    underdog_count = (h2h_df['odds_american'] > 0).sum()
    
    if favorite_count + underdog_count > 0:
        fav_pct = (favorite_count / (favorite_count + underdog_count)) * 100
        dog_pct = (underdog_count / (favorite_count + underdog_count)) * 100
        
        print(f"  Favorites: {favorite_count:2d} picks ({fav_pct:5.1f}%)")
        print(f"  Underdogs: {underdog_count:2d} picks ({dog_pct:5.1f}%)")

# Sport distribution
print("\n📊 SPORT DISTRIBUTION:")
print("-" * 80)
sport_counts = df['sport'].value_counts()
for sport, count in sport_counts.items():
    pct = (count / total_picks) * 100
    print(f"  {sport:10s}: {count:2d} picks ({pct:5.1f}%)")

# Confidence distribution
print("\n⭐ CONFIDENCE DISTRIBUTION:")
print("-" * 80)
confidence_counts = df['confidence'].value_counts().sort_index(ascending=False)
for conf, count in confidence_counts.items():
    pct = (count / total_picks) * 100
    print(f"  {conf}: {count:2d} picks ({pct:5.1f}%)")

# Check for patterns in reasoning
print("\n🔍 REASONING ANALYSIS:")
print("-" * 80)

# Count how many mention "two-source agreement"
two_source = df['reasoning'].str.contains('two-source', case=False, na=False).sum()
print(f"  Mentions 'two-source agreement': {two_source} picks")

# Count how many mention Kalshi
kalshi_mentions = df['reasoning'].str.contains('Kalshi', case=False, na=False).sum()
print(f"  Mentions 'Kalshi': {kalshi_mentions} picks")

# Count how many say "No Kalshi"
no_kalshi = df['reasoning'].str.contains('No Kalshi', case=False, na=False).sum()
print(f"  Says 'No Kalshi data': {no_kalshi} picks")

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)

issues = []

# Check for market bias
if market_counts.get('totals', 0) > total_picks * 0.7:
    issues.append("⚠️  TOTALS BIAS: 70%+ of picks are totals (should be ~33% if balanced)")

# Check for Over/Under bias
if len(totals_df) > 0 and under_count > over_count * 2:
    issues.append(f"⚠️  UNDER BIAS: {under_pct:.0f}% of totals are Under (should be ~50%)")

# Check for missing spreads
if spreads_df.empty:
    issues.append("⚠️  NO SPREADS: Zero spread picks (should have some)")

# Check for low H2H
if len(h2h_df) < total_picks * 0.1:
    issues.append(f"⚠️  LOW H2H: Only {len(h2h_df)} moneyline picks (should be ~33%)")

if issues:
    print("\n🚨 ISSUES DETECTED:\n")
    for issue in issues:
        print(f"  {issue}")
    
    print("\n💡 LIKELY CAUSES:")
    print("  1. Scraped data is heavily weighted toward totals")
    print("  2. Expert sources (OddsShark, OddsTrader, CBS) prefer totals")
    print("  3. AI prompt doesn't encourage market diversity")
    print("  4. Consensus requirement filters out spreads/H2H")
else:
    print("\n✅ No major bias detected - picks look balanced!")

print("\n" + "=" * 80)

