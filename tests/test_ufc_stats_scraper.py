#!/usr/bin/env python3
"""Test UFC Stats scraper to understand page structure."""

import requests
from bs4 import BeautifulSoup

url = "http://ufcstats.com/event-details/00e11b5c8b7bfeeb"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

try:
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    print("Page title:", soup.title.string if soup.title else "N/A")
    
    print("\nLooking for fight tables...")
    tables = soup.find_all("table")
    print("Found", len(tables), "tables")
    
    for i, table in enumerate(tables[:3]):
        print("\nTable", i, "class=", table.get('class'))
        rows = table.find_all("tr")
        print("  Rows:", len(rows))
        if rows:
            print("  First row cells:", len(rows[0].find_all('td')))
            if i == 0 and len(rows) > 1:
                print("  First row HTML:", rows[1].prettify()[:500])
    
    print("\nLooking for fighter names...")
    fighter_links = soup.find_all("a")
    print("Found", len(fighter_links), "links total")
    
    # Look for specific patterns
    for link in fighter_links[:20]:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        if 'fighter' in href.lower() or len(text) > 5:
            print(f"  Link: {text[:30]} -> {href[:50]}")
    
except Exception as e:
    print("Error:", e)
    import traceback
    traceback.print_exc()

