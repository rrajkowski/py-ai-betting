#!/usr/bin/env python3
"""Analyze CBS Sports HTML structure to understand how to scrape it."""

import requests
from bs4 import BeautifulSoup

url = 'https://www.cbssports.com/nfl/picks/experts/'
resp = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}, timeout=15)

soup = BeautifulSoup(resp.text, 'html.parser')

# Find Miami/Pittsburgh row
rows = soup.select('tbody tr')
for i, row in enumerate(rows):
    text = row.get_text()
    if 'MIA' in text and 'PIT' in text:
        print(f'=== Miami @ Pittsburgh (Row {i}) ===\n')

        # Get all cells
        cells = row.select('td')
        print(f'Total cells: {len(cells)}\n')

        for j, cell in enumerate(cells):
            print(f'--- Cell {j} ---')
            print(f'Text: {cell.get_text(strip=True)[:150]}')

            # Check for team logos
            logos = cell.select('.TeamLogo-image')
            if logos:
                print(f'Team logos: {len(logos)}')
                for logo in logos:
                    src = logo.get('src', '')
                    if 'pittsburgh' in src.lower():
                        print('  - Pittsburgh')
                    elif 'miami' in src.lower():
                        print('  - Miami')

            # Check for picks (buttons or divs)
            picks = cell.select('.TableExpertPicks-pickLayout')
            if picks:
                print(f'Picks found: {len(picks)}')
                for pick in picks:
                    # Get team from logo
                    pick_logo = pick.select_one('.TeamLogo-image')
                    if pick_logo:
                        src = pick_logo.get('src', '')
                        if 'pittsburgh' in src.lower():
                            print('  Pick: Pittsburgh')
                        elif 'miami' in src.lower():
                            print('  Pick: Miami')

                    # Get spread from button
                    button = pick.select_one('button')
                    if button:
                        config = button.get('data-config', '')
                        if 'line' in config:
                            # Extract line from JSON
                            import json
                            try:
                                config_data = json.loads(config)
                                line = config_data.get('line', '')
                                market = config_data.get('marketName', '')
                                print(f'    Market: {market}, Line: {line}')
                            except (json.JSONDecodeError, KeyError, TypeError):
                                pass

            print()

        break
