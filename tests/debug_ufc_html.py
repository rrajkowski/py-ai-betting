#!/usr/bin/env python3
"""Debug UFC Stats HTML structure for Krylov fight."""

import requests
from bs4 import BeautifulSoup

url = "http://ufcstats.com/event-details/00e11b5c8b7bfeeb"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=15)
soup = BeautifulSoup(resp.text, "html.parser")

# Find the fight table
fight_table = soup.find("table", {"class": "b-fight-details__table"})
rows = fight_table.find_all("tr", {"class": "b-fight-details__table-row"})

print(f"Total rows: {len(rows)}\n")

# Look for Krylov fight
for i, row in enumerate(rows):
    links = row.find_all("a", {"href": lambda x: x and "/fighter-details/" in x if x else False})
    if links and len(links) >= 2:
        fighter1 = links[0].get_text(strip=True)
        fighter2 = links[1].get_text(strip=True)
        
        if "Krylov" in fighter1 or "Krylov" in fighter2:
            print(f"Found Krylov fight at row {i}!")
            print(f"Fighter 1: {fighter1}")
            print(f"Fighter 2: {fighter2}")
            print(f"\nRow HTML:")
            print(row.prettify()[:2000])
            print("\nRow text:")
            print(row.get_text()[:500])

