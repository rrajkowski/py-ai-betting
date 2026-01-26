#!/usr/bin/env python3
"""Debug score extraction from UFC Stats."""

import requests
from bs4 import BeautifulSoup

url = "http://ufcstats.com/event-details/00e11b5c8b7bfeeb"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

resp = requests.get(url, headers=headers, timeout=30)
soup = BeautifulSoup(resp.text, "html.parser")

fight_table = soup.find("table", {"class": "b-fight-details__table"})
rows = fight_table.find_all("tr", {"class": "b-fight-details__table-row"})

for i, row in enumerate(rows):
    links = row.find_all("a", {"href": lambda x: x and "/fighter-details/" in x if x else False})
    if links and len(links) >= 2:
        fighter1 = links[0].get_text(strip=True)
        fighter2 = links[1].get_text(strip=True)
        
        if "Krylov" in fighter1 or "Krylov" in fighter2:
            print(f"Found Krylov fight!")
            print(f"Fighter 1: {fighter1}")
            print(f"Fighter 2: {fighter2}")
            
            cells = row.find_all("td")
            print(f"\nTotal cells: {len(cells)}")
            
            for j, cell in enumerate(cells[:5]):
                print(f"\nCell {j}:")
                print(f"  Text: {cell.get_text(strip=True)[:100]}")
                
                # Try to extract scores
                if j == 2:
                    score_text = cell.get_text(strip=True)
                    print(f"  Full text: {score_text}")
                    
                    # Try different parsing methods
                    parts = score_text.split()
                    print(f"  Split parts: {parts}")
                    
                    # Get all p tags
                    p_tags = cell.find_all("p")
                    print(f"  P tags: {len(p_tags)}")
                    for p in p_tags:
                        print(f"    - {p.get_text(strip=True)}")

