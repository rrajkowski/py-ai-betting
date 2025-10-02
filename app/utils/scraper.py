import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from app.utils.db import insert_context


def scrape_oddsshark_consensus(target_date: str, sport: str):
    """
    Scrapes OddsShark's computer picks page for expert consensus data for a single sport.
    Uses requests + BeautifulSoup (no Playwright).
    """

    # Map internal sport key to OddsShark URL segment (e.g., americanfootball_nfl -> nfl)
    sport_segment = sport.split('_')[-1].lower()
    url = f"https://www.oddsshark.com/{sport_segment}/computer-picks"

    print(f"📡 Scraper starting for OddsShark on {sport.upper()} at {url}...")

    sport_name_upper = sport.split('_')[-1].upper()

    try:
        # Fetch the page
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Collect all event containers
        game_containers = soup.select(
            ".computer-picks-content .computer-picks-event-container")
        print(
            f"🔍 Found {len(game_containers)} game containers for {sport_name_upper}.")

        scraped_picks_count = 0

        for index, container in enumerate(game_containers):
            try:
                # --- 1. Extract Game Data and Date ---
                event_date_element = container.select_one(
                    ".odds--group__event-container")
                if event_date_element and event_date_element.has_attr("data-event-date"):
                    try:
                        timestamp = int(event_date_element["data-event-date"])
                        game_date_utc = datetime.fromtimestamp(
                            timestamp, tz=timezone.utc
                        ).strftime("%Y-%m-%d")
                    except ValueError:
                        game_date_utc = target_date
                else:
                    game_date_utc = target_date

                # Team Names
                teams = []
                team_names_container = container.select_one(".team-names")
                if team_names_container:
                    raw_text = team_names_container.get_text(" ", strip=True)
                    if "VS" in raw_text:
                        teams = [t.strip()
                                 for t in raw_text.split("VS") if t.strip()]

                if len(teams) < 2:
                    matchup_link = container.select_one(".matchup-link")
                    if matchup_link:
                        matchup_text = matchup_link.get_text(strip=True)
                        if "@" in matchup_text:
                            teams = [t.strip()
                                     for t in matchup_text.split("@")]

                if len(teams) < 2:
                    game_title = f"Game {index}"
                    game_id = f"{sport_name_upper}-{target_date}-Game{index}"
                else:
                    team_a, team_b = teams[0].strip(), teams[1].strip()
                    game_title = f"{team_a} vs {team_b}"
                    game_id = (
                        f"{sport_name_upper}-{game_date_utc}-"
                        f"{team_a.replace(' ', '')}vs{team_b.replace(' ', '')}"
                    )

                # --- 2. Extract Consensus Picks ---
                def normalize(sel):
                    el = container.select_one(sel)
                    return el.get_text(" ", strip=True) if el else ""

                ml_pick = normalize(".predicted-score .highlighted-pick")
                spread_pick = normalize(".spread-pick .highlighted-pick")
                total_pick = normalize(".total-pick .highlighted-pick")

                # --- 3. Normalize + Insert ---
                consensus_data = {
                    "game_title": game_title,
                    "ml_pick_raw": ml_pick,
                    "spread_pick_raw": spread_pick,
                    "total_pick_raw": total_pick,
                    "extraction_date": datetime.now(timezone.utc).isoformat(),
                }

                insert_context(
                    category="storage",
                    context_type="expert_consensus",
                    game_id=game_id,
                    match_date=game_date_utc,
                    sport=sport_name_upper,
                    data=consensus_data,
                    source="oddsshark",
                )
                scraped_picks_count += 1

            except Exception as container_e:
                print(
                    f"⚠️ Could not parse container #{index} on {sport_name_upper}: {container_e}")
                continue

        print(
            f"✅ Scraper finished. Stored {scraped_picks_count} picks for {sport_name_upper}.")

    except Exception as e:
        print(f"❌ Scrape failed fatally for {sport.upper()} on {url}: {e}")
        raise


def run_scrapers(target_date: str, sport: str):
    """Entrypoint for scraping a single sport."""
    scrape_oddsshark_consensus(target_date, sport)
