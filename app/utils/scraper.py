import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from app.utils.db import insert_context


def scrape_oddsshark_consensus(target_date: str, sport: str):
    """
    Scrapes OddsShark's computer picks page for consensus and odds data (2025 HTML format).
    Works for NFL, NCAAF, MLB, NBA, etc.
    """

    sport_segment = sport.split('_')[-1].lower()
    url = f"https://www.oddsshark.com/{sport_segment}/computer-picks"
    sport_name_upper = sport_segment.upper()

    print(
        f"📡 Scraper starting for OddsShark on {sport_name_upper} at {url}...")

    try:
        resp = requests.get(url, headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        game_containers = soup.select(".computer-picks-event-container")
        print(
            f"🔍 Found {len(game_containers)} game containers for {sport_name_upper}.")

        scraped_picks_count = 0

        for index, container in enumerate(game_containers[:50]):
            try:
                # 1️⃣ Parse timestamp
                date_tag = container.select_one(
                    ".odds--group__event-container")
                if date_tag and date_tag.has_attr("data-event-date"):
                    try:
                        ts = int(date_tag["data-event-date"])
                        game_date_utc = datetime.fromtimestamp(
                            ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    except Exception:
                        game_date_utc = target_date
                else:
                    game_date_utc = target_date

                # 2️⃣ Teams - Updated parsing for 2025 structure
                team_spans = container.select(".team-names span")
                teams = []

                # Filter out "VS" and empty spans to get team names
                for span in team_spans:
                    text = span.get_text(strip=True)
                    if text and text not in ["VS", "vs", "V", "v", "@"]:
                        teams.append(text)

                # Fallback: try matchup link
                if len(teams) < 2:
                    link = container.select_one("a.matchup-link")
                    if link:
                        link_text = link.text.strip()
                        if "vs" in link_text.lower():
                            teams = [t.strip() for t in link_text.split("vs")]
                        elif "@" in link_text:
                            teams = [t.strip() for t in link_text.split("@")]

                if len(teams) < 2:
                    continue

                team_a, team_b = teams
                game_title = f"{team_a} @ {team_b}"
                game_id = f"{sport_name_upper}-{team_a.replace(' ', '')}-vs-{team_b.replace(' ', '')}-{target_date}"

                # --- helper
                def parse_odds(text):
                    try:
                        val = int(text.replace(
                            "+", "").replace("−", "-").strip())
                        return val if -600 <= val <= 600 else None
                    except ValueError:
                        return None

                # 3️⃣ Moneyline - Updated for 2025 structure
                ml_picks = []
                predicted_score_section = container.select_one(
                    ".predicted-score")
                if predicted_score_section:
                    # Look for team shortnames and money values
                    for row in predicted_score_section.select("div"):
                        team_code = None
                        money_value = None

                        # Find team shortname
                        short_tag = row.select_one("span.team-shortname")
                        if short_tag:
                            team_code = short_tag.text.strip()

                        # Find money value
                        money_tag = row.select_one("span.money-value")
                        if money_tag:
                            money_value = money_tag.text.strip()

                        if team_code and money_value:
                            val = parse_odds(money_value)
                            if val is not None:
                                ml_picks.append(
                                    {"team": team_code, "market": "moneyline", "odds_american": val})

                # 4️⃣ Spread - Updated for 2025 structure
                spread_picks = []
                spread_section = container.select_one(".spread-pick")
                if spread_section:
                    for row in spread_section.select("div"):
                        spread_line_tag = row.select_one(
                            "span.highlighted-text.spread-text")
                        if spread_line_tag:
                            line = spread_line_tag.text.strip()

                            # Look for odds in various possible locations
                            odds_tag = (
                                row.select_one("span.spread-cell") or
                                row.select_one(".best-spread-container span:last-child") or
                                row.select_one("span:last-child")
                            )

                            if odds_tag:
                                val = parse_odds(odds_tag.text)
                                if val is not None:
                                    spread_picks.append(
                                        {"market": "spread", "line": line, "odds_american": val})

                # 5️⃣ Total - Updated for 2025 structure
                total_picks = []
                total_section = container.select_one(".total-pick")
                if total_section:
                    for row in total_section.select("div"):
                        total_line_tag = row.select_one(
                            "span.highlighted-text")
                        if total_line_tag:
                            line = total_line_tag.text.strip()

                            # Look for odds in various possible locations
                            odds_tag = (
                                row.select_one(".best-total-container span:last-child") or
                                row.select_one("span:last-child")
                            )

                            if odds_tag:
                                val = parse_odds(odds_tag.text)
                                if val is not None:
                                    total_picks.append(
                                        {"market": "total", "line": line, "odds_american": val})

                all_picks = ml_picks + spread_picks + total_picks
                if not all_picks:
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

            except Exception:
                continue

        print(
            f"✅ Scraper finished. Stored {scraped_picks_count} games for {sport_name_upper}.")

    except Exception as e:
        print(f"❌ Fatal scrape error for {sport_name_upper} at {url}: {e}")
        raise


def run_scrapers(target_date: str, sport: str):
    """Entrypoint for scraping a single sport."""
    scrape_oddsshark_consensus(target_date, sport)
