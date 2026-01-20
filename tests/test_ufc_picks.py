#!/usr/bin/env python3
"""Test UFC picks generation to debug the issue."""

import sys
from datetime import datetime, timezone
from app.utils.sport_config import SportConfig
from app.utils.kalshi_api import fetch_kalshi_consensus
from app.rage_picks import fetch_odds
from app.utils.scraper import run_scrapers

# Test 1: Check if UFC is in season
print("=" * 60)
print("TEST 1: Check if UFC is in season")
print("=" * 60)
is_in_season = SportConfig.is_in_season("mma_mixed_martial_arts")
print(f"UFC in season: {is_in_season}")

# Test 2: Check Kalshi config
print("\n" + "=" * 60)
print("TEST 2: Check Kalshi config for UFC")
print("=" * 60)
kalshi_config = SportConfig.KALSHI_CONFIG.get("mma_mixed_martial_arts")
print(f"Kalshi config: {kalshi_config}")

# Test 3: Fetch Kalshi consensus
print("\n" + "=" * 60)
print("TEST 3: Fetch Kalshi consensus for UFC")
print("=" * 60)
target_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
print(f"Target date: {target_date}")
try:
    fetch_kalshi_consensus("mma_mixed_martial_arts", target_date)
    print("✅ Kalshi consensus fetch completed")
except Exception as e:
    print(f"❌ Error fetching Kalshi consensus: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Fetch odds
print("\n" + "=" * 60)
print("TEST 4: Fetch odds for UFC")
print("=" * 60)
try:
    odds = fetch_odds("mma_mixed_martial_arts")
    print(f"✅ Found {len(odds)} upcoming UFC games with odds")
    if odds:
        print(f"First game: {odds[0]}")
except Exception as e:
    print(f"❌ Error fetching odds: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Run scrapers
print("\n" + "=" * 60)
print("TEST 5: Run scrapers for UFC")
print("=" * 60)
try:
    run_scrapers(target_date, "mma_mixed_martial_arts")
    print("✅ Scrapers completed")
except Exception as e:
    print(f"❌ Error running scrapers: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("All tests completed!")
print("=" * 60)

