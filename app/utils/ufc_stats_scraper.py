#!/usr/bin/env python3
"""
UFC Stats Scraper - Fallback scoring for UFC/MMA picks when Odds API lacks data.

Scrapes completed UFC fights from ufcstats.com and matches them with pending picks.
"""

from app.db import get_db, update_pick_result
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


def scrape_ufc_event(event_url: str) -> dict:
    """
    Scrape a single UFC event page for fight results.

    Args:
        event_url: Full URL to UFC Stats event page

    Returns:
        Dict with event_date and list of fights with fighter names and winner
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(event_url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Extract event date from page
        event_date = None
        date_elem = soup.find("span", {"class": "b-list__box-list-item-date"})
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            try:
                event_date = datetime.strptime(
                    date_text, "%B %d, %Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Find all fight rows
        fights = []
        fight_table = soup.find("table", {"class": "b-fight-details__table"})

        if fight_table:
            rows = fight_table.find_all(
                "tr", {"class": "b-fight-details__table-row"})
            for row in rows:
                # Get all links in the row (fighter names are links)
                links = row.find_all(
                    "a", {"href": lambda x: x and "/fighter-details/" in x if x else False})

                if len(links) >= 2:
                    fighter1 = links[0].get_text(strip=True)
                    fighter2 = links[1].get_text(strip=True)

                    # Determine winner by checking for "win" indicator in first cell
                    cells = row.find_all("td")
                    winner = None

                    # Check if first cell contains "win" (indicates fighter1 won)
                    if cells and "win" in cells[0].get_text().lower():
                        winner = fighter1
                    # Check if second cell (fighter names) has "win" indicator
                    elif len(cells) > 1 and "win" in cells[1].get_text().lower():
                        # If win is in the second cell, it's for fighter2
                        # But we need to check position - if it's before fighter2, it's fighter1
                        cell_text = cells[1].get_text()
                        fighter1_pos = cell_text.find(fighter1)
                        fighter2_pos = cell_text.find(fighter2)
                        win_pos = cell_text.lower().find("win")

                        if win_pos < fighter2_pos:
                            winner = fighter1
                        else:
                            winner = fighter2

                    # Extract round information
                    # Column structure: Win | Fighters | Scores | Strikes | Takedowns | Submissions | Weight | Finish | Round | Time
                    # The round column is at index 8 (9th cell)
                    round_ended = None
                    if len(cells) > 8:
                        # Get the round cell (index 8)
                        round_cell = cells[8].get_text(strip=True)
                        try:
                            round_ended = int(round_cell)
                        except (ValueError, IndexError):
                            pass

                    fights.append({
                        "away_fighter": fighter1,
                        "home_fighter": fighter2,
                        "winner": winner,
                        "round_ended": round_ended,
                        "event_date": event_date
                    })

        return {"event_date": event_date, "fights": fights}

    except Exception as e:
        print(f"Error scraping UFC event {event_url}: {e}")
        return {"event_date": None, "fights": []}


def find_pending_ufc_picks() -> list:
    """Get all pending UFC picks from database."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, game, pick, market, sport FROM ai_picks WHERE sport='UFC' AND result='Pending'"
    )
    picks = [dict(row) for row in cur.fetchall()]
    conn.close()
    return picks


def match_fight_to_pick(fight: dict, pick: dict) -> bool:
    """
    Check if a fight matches a pick.

    Returns True if the fight is for this pick's game.
    """
    game = pick['game']  # Format: "Away Fighter @ Home Fighter"
    if ' @ ' not in game:
        return False

    away_fighter, home_fighter = game.split(' @ ')

    # Normalize names for comparison
    away_fighter = away_fighter.strip().lower()
    home_fighter = home_fighter.strip().lower()
    fight_away = fight['away_fighter'].strip(
    ).lower() if fight['away_fighter'] else ""
    fight_home = fight['home_fighter'].strip(
    ).lower() if fight['home_fighter'] else ""

    # Check if fighters match
    return (away_fighter == fight_away and home_fighter == fight_home)


def grade_pick_from_fight(pick: dict, fight: dict) -> str:
    """
    Determine if pick won based on fight result.

    Supports:
    - h2h (moneyline): Pick fighter name
    - totals (over/under rounds): Pick format like "Under 2.5 rounds" or "Over 3.5 rounds"

    Returns: 'Win', 'Loss', or 'Pending'
    """
    market = pick.get('market', '').lower()

    # Handle h2h (moneyline) picks
    if market == 'h2h':
        if not fight['winner']:
            return 'Pending'

        picked_fighter = pick['pick'].strip().lower()
        winner = fight['winner'].strip().lower()

        if picked_fighter == winner:
            return 'Win'
        else:
            return 'Loss'

    # Handle totals (over/under rounds) picks
    elif market == 'totals':
        if fight['round_ended'] is None:
            return 'Pending'

        pick_text = pick['pick'].strip().lower()

        # Parse pick format: "Under 2.5 rounds" or "Over 3.5 rounds"
        if 'under' in pick_text:
            # Extract the round number (e.g., "2.5" from "Under 2.5 rounds")
            parts = pick_text.split()
            try:
                round_limit = float(parts[1])
                # Under means fight ended before the limit
                # Round 1 = 1, Round 2 = 2, etc.
                if fight['round_ended'] < round_limit:
                    return 'Win'
                elif fight['round_ended'] > round_limit:
                    return 'Loss'
                else:
                    # Exact match (e.g., 2.5 rounds) - typically a push
                    return 'Push'
            except (ValueError, IndexError):
                return 'Pending'

        elif 'over' in pick_text:
            # Extract the round number
            parts = pick_text.split()
            try:
                round_limit = float(parts[1])
                # Over means fight ended after the limit
                if fight['round_ended'] > round_limit:
                    return 'Win'
                elif fight['round_ended'] < round_limit:
                    return 'Loss'
                else:
                    # Exact match - typically a push
                    return 'Push'
            except (ValueError, IndexError):
                return 'Pending'

    return 'Pending'


def update_historical_games(fight: dict):
    """Store fight result in historical_games table."""
    conn = get_db()
    cur = conn.cursor()

    game_id = f"UFC_{fight['away_fighter']}_{fight['home_fighter']}_{fight['event_date']}"
    game_str = f"{fight['away_fighter']} @ {fight['home_fighter']}"

    cur.execute("""
        INSERT OR REPLACE INTO historical_games 
        (id, sport, game, winner, date, home_team, away_team)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        game_id,
        "UFC",
        game_str,
        fight['winner'],
        fight['event_date'],
        fight['home_fighter'],
        fight['away_fighter']
    ))

    conn.commit()
    conn.close()


def process_ufc_event(event_url: str) -> dict:
    """
    Main function: Scrape event and grade matching picks.

    Returns: Summary of picks graded
    """
    print(f"\n🥊 Processing UFC event: {event_url}")

    # Scrape the event
    event_data = scrape_ufc_event(event_url)
    if not event_data['fights']:
        print("⚠️ No fights found in event")
        return {"graded": 0, "skipped": 0}

    print(f"✅ Found {len(event_data['fights'])} fights")

    # Get pending picks
    pending_picks = find_pending_ufc_picks()
    print(f"📋 Found {len(pending_picks)} pending UFC picks")

    graded = 0
    skipped = 0

    # Match fights to picks
    for fight in event_data['fights']:
        for pick in pending_picks:
            if match_fight_to_pick(fight, pick):
                result = grade_pick_from_fight(pick, fight)

                if result != 'Pending':
                    update_pick_result(pick['id'], result)
                    update_historical_games(fight)
                    print(
                        f"✅ Graded pick #{pick['id']}: {pick['game']} - {pick['pick']} = {result}")
                    graded += 1
                    pending_picks.remove(pick)  # Remove from list
                else:
                    skipped += 1

    return {"graded": graded, "skipped": skipped}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 app/utils/ufc_stats_scraper.py <event_url>")
        print("Example: python3 app/utils/ufc_stats_scraper.py http://ufcstats.com/event-details/00e11b5c8b7bfeeb")
        sys.exit(1)

    event_url = sys.argv[1]
    result = process_ufc_event(event_url)
    print(
        f"\n📊 Summary: Graded {result['graded']} picks, Skipped {result['skipped']}")
