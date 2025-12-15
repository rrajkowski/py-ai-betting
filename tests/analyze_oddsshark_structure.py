#!/usr/bin/env python3
"""Analyze OddsShark HTML structure to find spread and total picks."""

import requests
from bs4 import BeautifulSoup

url = 'https://www.oddsshark.com/nfl/computer-picks'
resp = requests.get(url, headers={
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}, timeout=15)

soup = BeautifulSoup(resp.text, 'html.parser')

# Find Miami/Pittsburgh game
containers = soup.select('.computer-picks-event-container')
print(
    f'Total game containers (.computer-picks-event-container): {len(containers)}\n')

for container in containers:
    text = container.get_text()
    if 'Miami' in text and 'Pittsburgh' in text:
        print('=== Miami @ Pittsburgh ===\n')

        # Get matchup info
        matchup = container.select_one('.matchup-info')
        if matchup:
            print(f'Matchup: {matchup.get_text(strip=True)[:100]}\n')

        # Look for spread pick
        spread_section = container.select_one('.spread-pick')
        if spread_section:
            print('SPREAD PICK FOUND:')
            print(f'  Text: {spread_section.get_text(strip=True)[:200]}')

            # Show HTML structure
            print('  HTML structure:')
            for elem in spread_section.select('*')[:10]:
                tag = elem.name
                classes = ' '.join(elem.get('class', []))
                text = elem.get_text(strip=True)[:50]
                print(f'    <{tag} class="{classes}">: {text}')
            print()
        else:
            print('❌ No .spread-pick section\n')

        # Look for total pick
        total_section = container.select_one('.total-pick')
        if total_section:
            print('TOTAL PICK FOUND:')
            print(f'  Text: {total_section.get_text(strip=True)[:200]}')

            # Show HTML structure
            print('  HTML structure:')
            for elem in total_section.select('*')[:10]:
                tag = elem.name
                classes = ' '.join(elem.get('class', []))
                text = elem.get_text(strip=True)[:50]
                print(f'    <{tag} class="{classes}">: {text}')
            print()
        else:
            print('❌ No .total-pick section\n')

        # Look for predicted score section
        predicted_score = container.select_one('.predicted-score')
        if predicted_score:
            print('PREDICTED SCORE SECTION:')
            print(f'  {predicted_score.get_text(strip=True)[:300]}\n')

            # Show HTML structure
            print('HTML structure:')
            for div in predicted_score.select('div')[:5]:
                print(f'  <div>: {div.get_text(strip=True)[:100]}')

        # Look for all sections
        print('\nAll sections in container:')
        for section in container.select('div[class*="pick"], div[class*="score"]'):
            classes = ' '.join(section.get('class', []))
            print(f'  .{classes}: {section.get_text(strip=True)[:80]}')

        break
