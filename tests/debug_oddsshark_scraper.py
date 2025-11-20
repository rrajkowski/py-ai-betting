"""Debug OddsShark scraper to see why it's only collecting totals."""

import requests
from bs4 import BeautifulSoup

# Test with NFL (most likely to have all markets)
sport = "nfl"
url = f"https://www.oddsshark.com/{sport}/computer-picks"

print("=" * 80)
print(f"DEBUGGING ODDSSHARK SCRAPER - {sport.upper()}")
print("=" * 80)
print(f"\nURL: {url}\n")

try:
    resp = requests.get(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }, timeout=15)
    resp.raise_for_status()
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Find game containers
    game_containers = soup.select(".computer-picks-event-container")
    print(f"✅ Found {len(game_containers)} game containers\n")
    
    if not game_containers:
        print("❌ No game containers found!")
        print("\nTrying alternative selectors...")
        
        # Try other possible selectors
        alternatives = [
            ".game-container",
            ".event-container",
            "[class*='computer-picks']",
            "[class*='event']",
        ]
        
        for selector in alternatives:
            containers = soup.select(selector)
            if containers:
                print(f"  ✅ Found {len(containers)} with selector: {selector}")
    else:
        # Analyze first game in detail
        first_game = game_containers[0]
        
        print("=" * 80)
        print("ANALYZING FIRST GAME:")
        print("=" * 80)
        
        # Check for moneyline section
        print("\n1️⃣ MONEYLINE SECTION:")
        print("-" * 80)
        ml_section = first_game.select_one(".predicted-score")
        if ml_section:
            print("✅ Found .predicted-score section")
            
            # Look for team shortnames
            shortnames = ml_section.select("span.team-shortname")
            print(f"   Team shortnames found: {len(shortnames)}")
            for sn in shortnames:
                print(f"     - {sn.text.strip()}")
            
            # Look for money values
            money_values = ml_section.select("span.money-value")
            print(f"   Money values found: {len(money_values)}")
            for mv in money_values:
                print(f"     - {mv.text.strip()}")
            
            if not shortnames or not money_values:
                print("\n   ⚠️ Missing data - checking HTML structure:")
                print(f"   {ml_section.prettify()[:500]}...")
        else:
            print("❌ No .predicted-score section found")
            print("   Checking for alternative selectors...")
            
            alternatives = [
                ".moneyline-pick",
                ".ml-pick",
                "[class*='moneyline']",
                "[class*='predicted']",
            ]
            
            for selector in alternatives:
                alt = first_game.select_one(selector)
                if alt:
                    print(f"   ✅ Found alternative: {selector}")
                    print(f"      {alt.prettify()[:200]}...")
        
        # Check for spread section
        print("\n2️⃣ SPREAD SECTION:")
        print("-" * 80)
        spread_section = first_game.select_one(".spread-pick")
        if spread_section:
            print("✅ Found .spread-pick section")
            
            # Look for spread lines
            spread_lines = spread_section.select("span.highlighted-text.spread-text")
            print(f"   Spread lines found: {len(spread_lines)}")
            for sl in spread_lines:
                print(f"     - {sl.text.strip()}")
            
            # Look for odds
            odds_tags = spread_section.select("span.spread-cell")
            print(f"   Odds tags found: {len(odds_tags)}")
            for ot in odds_tags:
                print(f"     - {ot.text.strip()}")
            
            if not spread_lines:
                print("\n   ⚠️ Missing spread lines - checking HTML structure:")
                print(f"   {spread_section.prettify()[:500]}...")
        else:
            print("❌ No .spread-pick section found")
            print("   Checking for alternative selectors...")
            
            alternatives = [
                ".spread",
                "[class*='spread']",
            ]
            
            for selector in alternatives:
                alt = first_game.select_one(selector)
                if alt:
                    print(f"   ✅ Found alternative: {selector}")
                    print(f"      {alt.prettify()[:200]}...")
        
        # Check for total section
        print("\n3️⃣ TOTAL SECTION:")
        print("-" * 80)
        total_section = first_game.select_one(".total-pick")
        if total_section:
            print("✅ Found .total-pick section")
            
            # Look for total lines
            total_lines = total_section.select("span.highlighted-text")
            print(f"   Total lines found: {len(total_lines)}")
            for tl in total_lines:
                print(f"     - {tl.text.strip()}")
            
            # Look for odds
            odds_tags = total_section.select("span:last-child")
            print(f"   Odds tags found: {len(odds_tags)}")
            for ot in odds_tags[:3]:  # Limit to first 3
                print(f"     - {ot.text.strip()}")
        else:
            print("❌ No .total-pick section found")
        
        # Show full HTML structure of first game (truncated)
        print("\n" + "=" * 80)
        print("FULL HTML STRUCTURE (first 1000 chars):")
        print("=" * 80)
        print(first_game.prettify()[:1000])
        print("...")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("DIAGNOSIS:")
print("=" * 80)
print("""
If you see:
- ✅ All three sections found → Scraper code is correct, data is being collected
- ❌ Only total section found → OddsShark only shows totals on this page
- ❌ No sections found → HTML structure changed, need to update selectors

Next steps:
1. If sections are found but data is empty → Update CSS selectors
2. If only totals section exists → OddsShark may not show ML/spreads on computer picks page
3. If HTML structure changed → Need to rewrite scraper for new structure
""")

