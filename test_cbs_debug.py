"""Debug script to check CBS Sports HTML structure."""

import requests
from bs4 import BeautifulSoup

url = "https://www.cbssports.com/nba/expert-picks/"

print(f"🔍 Fetching {url}...")

resp = requests.get(url, headers={
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
}, timeout=15)

print(f"✅ Status: {resp.status_code}")

soup = BeautifulSoup(resp.text, "html.parser")

# Try different selectors
print("\n" + "=" * 80)
print("TESTING SELECTORS:")
print("=" * 80)

selectors = [
    "td.game-info-td",
    "div.game-info",
    "table",
    "tr",
    "div.picks-td",
    "div.expert-picks-col",
    "div.expert-spread",
    "div.expert-ou"
]

for selector in selectors:
    elements = soup.select(selector)
    print(f"\n{selector}: {len(elements)} found")
    if len(elements) > 0 and len(elements) < 20:
        for i, elem in enumerate(elements[:3], 1):
            print(f"  {i}. {elem.name} - {elem.get('class', [])}")

# Check for any table-like structures
print("\n" + "=" * 80)
print("LOOKING FOR GAME DATA:")
print("=" * 80)

# Look for team names
team_elements = soup.find_all(text=lambda t: t and any(team in str(t).upper() for team in ["TORONTO", "PHILADELPHIA", "CHARLOTTE", "INDIANA"]))
print(f"\nFound {len(team_elements)} elements with team names")
for elem in team_elements[:5]:
    parent = elem.parent
    print(f"  - '{elem.strip()}' in <{parent.name} class='{parent.get('class', [])}'>")

# Save HTML to file for inspection
with open("cbs_debug.html", "w") as f:
    f.write(soup.prettify())
print("\n✅ Saved HTML to cbs_debug.html for inspection")

