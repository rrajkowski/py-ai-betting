import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from app.utils.db import insert_context


def scrape_oddsshark_consensus(target_date: str, sport: str):
    """
    Scrapes OddsShark's computer picks page for expert consensus data for a single sport.
    Uses requests + BeautifulSoup (no Playwright).
    Compatible with 2025 OddsShark HTML (NFL/NCAAF/MLB).
    """


    sport_segment = sport.split('_')[-1].lower()
    url = f"https://www.oddsshark.com/{sport_segment}/computer-picks"
    sport_name_upper = sport.split('_')[-1].upper()

    print(
        f"📡 Scraper starting for OddsShark on {sport_name_upper} at {url}...")

    try:
        # Fetch and parse HTML
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all game containers
        game_containers = soup.select(
            ".computer-picks-content .computer-picks-event-container")
        print(
            f"🔍 Found {len(game_containers)} game containers for {sport_name_upper}.")

        scraped_picks_count = 0

        # Limit to 50 for efficiency
        for index, container in enumerate(game_containers[:50]):
            try:
                # --- 1️⃣ Extract base info
                event_date_element = container.select_one(
                    ".odds--group__event-container")
                if event_date_element and event_date_element.has_attr("data-event-date"):
                    try:
                        ts = int(event_date_element["data-event-date"])
                        game_date_utc = datetime.fromtimestamp(
                            ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    except Exception:
                        game_date_utc = target_date
                else:
                    game_date_utc = target_date

                # --- 2️⃣ Teams
                teams = []
                team_names = container.select(".team-names span")
                if len(team_names) >= 3:
                    teams = [team_names[0].text.strip(
                    ), team_names[2].text.strip()]
                else:
                    link = container.select_one(".matchup-link")
                    if link and "@" in link.text:
                        teams = [t.strip() for t in link.text.split("@")]

                if len(teams) < 2:
                    print(f"⚠️ Skipping Game {index}: could not parse teams.")
                    continue

                team_a, team_b = teams
                game_title = f"{team_a} vs {team_b}"
                game_id = f"{sport_name_upper}-{game_date_utc}-{team_a.replace(' ', '')}vs{team_b.replace(' ', '')}"

                # --- 3️⃣ Extract market data
                def get_odds_value(txt):
                    try:
                        val = int(txt.replace("+", ""))
                        return val if -150 <= val <= 150 else None
                    except ValueError:
                        return None

                # Moneyline
                ml_section = container.select_one(".predicted-score")
                ml_picks = []
                if ml_section:
                    rows = ml_section.select(
                        "div.highlighted-pick, div:not(.highlighted-pick)")
                    for row in rows:
                        spans = row.select("span")
                        if len(spans) >= 3:
                            team_name = spans[0].text.strip()
                            odds_val = get_odds_value(spans[2].text.strip())
                            if odds_val is not None:
                                ml_picks.append(
                                    {"team": team_name, "market": "moneyline", "odds_american": odds_val})

                # Spread
                spread_section = container.select_one(".spread-pick")
                spread_picks = []
                if spread_section:
                    spans = spread_section.select("div")
                    for s in spans:
                        nums = s.select("span.highlighted-text")
                        if len(nums) >= 2:
                            line_txt = nums[0].text.strip()
                            odds_val = get_odds_value(nums[1].text.strip())
                            if odds_val is not None:
                                spread_picks.append(
                                    {"market": "spread", "line": line_txt, "odds_american": odds_val})

                # Totals
                total_section = container.select_one(".total-pick")
                total_picks = []
                if total_section:
                    spans = total_section.select("span.highlighted-text")
                    if len(spans) >= 2:
                        line_label = spans[0].text.strip()
                        odds_val = get_odds_value(spans[1].text.strip())
                        if odds_val is not None:
                            total_picks.append(
                                {"market": "total", "line": line_label, "odds_american": odds_val})

                all_picks = ml_picks + spread_picks + total_picks

                if not all_picks:
                    print(f"⚠️ No valid odds found for {game_title}.")
                    continue

                consensus_data = {
                    "game_title": game_title,
                    "match_date": game_date_utc,
                    "markets": all_picks,
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
                print(f"✅ Stored {game_title} ({len(all_picks)} markets)")

            except Exception as inner_e:
                print(f"⚠️ Error parsing container #{index}: {inner_e}")
                continue

        print(
            f"✅ Scraper finished. Stored {scraped_picks_count} games for {sport_name_upper}.")

    except Exception as e:
        print(f"❌ Fatal scrape error for {sport_name_upper} at {url}: {e}")
        raise


def run_scrapers(target_date: str, sport: str):
    """Entrypoint for scraping a single sport."""
    scrape_oddsshark_consensus(target_date, sport)
