#!/usr/bin/env python3
"""
Test Boyd's Bets pick parsing logic with real examples from the website.
"""
import re


def convert_fraction_to_decimal(text):
    """Convert fractions like ½, ¼, ¾ to decimal equivalents."""
    fraction_map = {
        '½': '.5',
        '¼': '.25',
        '¾': '.75',
        '⅓': '.33',
        '⅔': '.67',
        '⅛': '.125',
        '⅜': '.375',
        '⅝': '.625',
        '⅞': '.875'
    }
    for frac, dec in fraction_map.items():
        text = text.replace(frac, dec)
    return text


def parse_boyds_pick(pick_text):
    """Parse Boyd's Bets pick text into structured data."""
    pick_text_normalized = convert_fraction_to_decimal(pick_text)
    
    pick_data = {
        "pick_text": pick_text,
        "normalized": pick_text_normalized
    }
    
    # Format 1: Spread (e.g., "Jacksonville State -2½ -110")
    spread_match = re.search(
        r'(.+?)\s+([-+][\d.]+)\s+([-+]\d+)', pick_text_normalized)
    if spread_match:
        pick_data.update({
            "market": "spread",
            "team": spread_match.group(1).strip(),
            "line": spread_match.group(2),
            "odds": spread_match.group(3)
        })
        return pick_data
    
    # Format 2: Total (e.g., "Canisius under 139 -110")
    total_match = re.search(
        r'(.+?)\s+(over|under)\s+([\d.]+)\s+([-+]\d+)', pick_text_normalized, re.IGNORECASE)
    if total_match:
        pick_data.update({
            "market": "total",
            "team": total_match.group(1).strip(),
            "direction": total_match.group(2).lower(),
            "line": total_match.group(3),
            "odds": total_match.group(4)
        })
        return pick_data
    
    # Format 3: Moneyline (e.g., "Merrimack -170")
    moneyline_match = re.search(
        r'(.+?)\s+([-+]\d+)$', pick_text_normalized)
    if moneyline_match:
        pick_data.update({
            "market": "h2h",
            "team": moneyline_match.group(1).strip(),
            "odds": moneyline_match.group(2)
        })
        return pick_data
    
    pick_data["market"] = "FAILED_TO_PARSE"
    return pick_data


# Test cases from Boyd's Bets website
test_picks = [
    "Jacksonville State -2½ -110",
    "Merrimack -170",
    "Stanford +10 -110",
    "Merrimack -4 -110",
    "Louisville -8½ -105",
    "Canisius under 139 -110",
    "Notre Dame +4½ -115",
    "Canisius +7½ -115",
    "Fairfield -6½ -110",
    "Gonzaga under 155 -110",
    "New Mexico State +1½ -110",
    "Oregon -1 -115",
    "Louisville -9 -115"
]

print("=" * 80)
print("TESTING BOYD'S BETS PICK PARSING")
print("=" * 80)

success_count = 0
failed_count = 0

for pick in test_picks:
    result = parse_boyds_pick(pick)
    
    if result["market"] == "FAILED_TO_PARSE":
        print(f"\n❌ FAILED: {pick}")
        print(f"   Normalized: {result['normalized']}")
        failed_count += 1
    else:
        print(f"\n✅ SUCCESS: {pick}")
        print(f"   Market: {result['market']}")
        print(f"   Team: {result.get('team', 'N/A')}")
        if result['market'] == 'spread':
            print(f"   Line: {result['line']} | Odds: {result['odds']}")
        elif result['market'] == 'total':
            print(f"   Direction: {result['direction']} | Line: {result['line']} | Odds: {result['odds']}")
        elif result['market'] == 'h2h':
            print(f"   Odds: {result['odds']}")
        success_count += 1

print("\n" + "=" * 80)
print(f"RESULTS: {success_count}/{len(test_picks)} parsed successfully")
if failed_count > 0:
    print(f"⚠️  {failed_count} picks failed to parse")
else:
    print("✅ All picks parsed successfully!")
print("=" * 80)

