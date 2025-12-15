import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from app.utils.db import insert_context
from app.utils.sport_config import SportConfig
from app.utils.team_mapper import normalize_team_name


def create_game_id(team_a: str, team_b: str, sport: str, target_date: str) -> str:
    """
    Create a consistent game_id by normalizing team names.

    Args:
        team_a: First team name (raw from scraper)
        team_b: Second team name (raw from scraper)
        sport: Sport name (e.g., 'NBA', 'NFL')
        target_date: Date string (YYYY-MM-DD)

    Returns:
        Consistent game_id (e.g., 'NBA-CharlotteHornets-vs-IndianaPacers-2025-11-19')
    """
    # Normalize team names to canonical form
    norm_a = normalize_team_name(team_a, sport)
    norm_b = normalize_team_name(team_b, sport)

    # Remove spaces for game_id
    clean_a = norm_a.replace(' ', '')
    clean_b = norm_b.replace(' ', '')

    return f"{sport}-{clean_a}-vs-{clean_b}-{target_date}"


def scrape_oddsshark_consensus(target_date: str, sport: str):
    """
    Scrapes OddsShark's computer picks page with seasonal awareness and smart filtering.
    Optimized to only scrape in-season sports and upcoming games.

    Args:
        target_date: Target date for grouping (YYYY-MM-DD)
        sport: Sport key (e.g., 'americanfootball_nfl')
    """
    # 1. Check if sport is in season
    if not SportConfig.is_in_season(sport):
        print(f"📡 Scraper: Skipping {sport.upper()} - out of season")
        return

    # 2. Get dynamic limit for this sport
    dynamic_limit = SportConfig.get_dynamic_limit(sport)
    if dynamic_limit == 0:
        print(f"📡 Scraper: Skipping {sport.upper()} - no games expected today")
        return

    sport_segment = sport.split('_')[-1].lower()
    url = f"https://www.oddsshark.com/{sport_segment}/computer-picks"
    sport_name_upper = sport_segment.upper()

    print(
        f"📡 Scraper: Fetching {sport_name_upper} picks (limit: {dynamic_limit}) from {url}...")

    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        game_containers = soup.select(".computer-picks-event-container")
        print(
            f"🔍 Found {len(game_containers)} game containers for {sport_name_upper}")

        if not game_containers:
            print(f"⚠️ No game containers found for {sport_name_upper}")
            return

        scraped_picks_count = 0
        now_utc = datetime.now(timezone.utc)
        max_future_date = now_utc + timedelta(days=3)

        # Limit containers to process based on dynamic limit
        max_containers = min(len(game_containers), dynamic_limit * 2)

        for index, container in enumerate(game_containers[:max_containers]):
            try:
                # 1️⃣ Parse timestamp and filter for upcoming games only
                date_tag = container.select_one(
                    ".odds--group__event-container")
                game_datetime = None

                if date_tag and date_tag.has_attr("data-event-date"):
                    try:
                        ts = int(date_tag["data-event-date"])
                        game_datetime = datetime.fromtimestamp(
                            ts, tz=timezone.utc)
                        game_date_utc = game_datetime.strftime(
                            "%Y-%m-%dT%H:%M:%SZ")
                    except Exception:
                        game_date_utc = target_date
                else:
                    game_date_utc = target_date

                # Skip games that have already started or are too far in the future
                if game_datetime:
                    if game_datetime < now_utc:
                        continue  # Skip past games
                    if game_datetime > max_future_date:
                        continue  # Skip games more than 3 days out

                # Stop if we've reached our limit
                if scraped_picks_count >= dynamic_limit:
                    break

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
                game_id = create_game_id(
                    team_a, team_b, sport_name_upper, target_date)

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
                    # New structure: <div><span.team-shortname>BUF</span><span>23.9</span><span>-275</span></div>
                    for row in predicted_score_section.select("div"):
                        team_code = None
                        money_value = None

                        # Find team shortname
                        short_tag = row.select_one("span.team-shortname")
                        if short_tag:
                            team_code = short_tag.text.strip()

                            # Money value is in the last <span> tag (not .money-value)
                            all_spans = row.select("span")
                            if len(all_spans) >= 3:  # team, score, odds
                                money_value = all_spans[-1].text.strip()

                        if team_code and money_value:
                            val = parse_odds(money_value)
                            if val is not None:
                                ml_picks.append(
                                    {"team": team_code, "market": "moneyline", "odds_american": val})

                # 4️⃣ Spread - Updated for 2025 structure
                spread_picks = []
                spread_section = container.select_one(".spread-pick")
                if spread_section:
                    # New structure: <div><span.highlighted-text>-5.5</span><span>-110</span></div>
                    for row in spread_section.select("div"):
                        # Look for highlighted-text (not .spread-text)
                        spread_line_tag = row.select_one(
                            "span.highlighted-text")
                        if spread_line_tag:
                            line = spread_line_tag.text.strip()

                            # Odds are in the next span tag
                            all_spans = row.select("span")
                            if len(all_spans) >= 2:  # line, odds
                                odds_text = all_spans[-1].text.strip()
                                val = parse_odds(odds_text)
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

                # Store each pick separately for better AI context
                for pick in all_picks:
                    # Determine team_pick based on market type
                    if pick["market"] == "moneyline":
                        team_pick = pick.get("team", team_a)
                    elif pick["market"] == "spread":
                        # Spread line indicates which team (e.g., "+3.5" = underdog)
                        line = pick.get("line", "")
                        team_pick = team_a if "+" in line or line.startswith(
                            team_a[:3]) else team_b
                    elif pick["market"] == "total":
                        # Total doesn't have a specific team
                        team_pick = f"{team_a} vs {team_b}"
                    else:
                        team_pick = team_a

                    pick_data = {
                        "game_title": game_title,
                        "match_date": game_date_utc,
                        "market": pick["market"],
                        "line": pick.get("line", ""),
                        "odds_american": pick.get("odds_american", 0),
                        "extraction_date": datetime.now(timezone.utc).isoformat(),
                    }

                    insert_context(
                        category="expert_consensus",
                        context_type="oddsshark_pick",
                        game_id=game_id,
                        match_date=game_date_utc,
                        sport=sport_name_upper,
                        team_pick=team_pick,
                        data=pick_data,
                        source="oddsshark",
                    )

                scraped_picks_count += 1

            except Exception as e:
                # Log parsing errors but continue
                if index < 5:  # Only log first few errors to avoid spam
                    print(f"⚠️ Error parsing container {index}: {e}")
                continue

        print(
            f"✅ Scraper: Stored {scraped_picks_count}/{len(game_containers)} games for {sport_name_upper}")

    except requests.exceptions.Timeout:
        print(f"❌ Scraper timeout for {sport_name_upper} at {url}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error for {sport_name_upper}: {e.response.status_code}")
    except Exception as e:
        print(f"❌ Fatal scrape error for {sport_name_upper}: {e}")


def scrape_oddstrader_picks(target_date: str, sport: str):
    """
    Scrapes OddsTrader expert picks (3-4 star ratings) for ML, Spread, and Totals.

    NOTE: OddsTrader is a fully JavaScript-rendered React app that requires
    pyppeteer/playwright to scrape. These tools don't work on Streamlit Cloud
    due to threading/signal limitations. This scraper is DISABLED for now.

    Alternative: Use OddsShark and CBS Sports for consensus data.

    Args:
        target_date: Target date for grouping (YYYY-MM-DD)
        sport: Sport key (e.g., 'americanfootball_nfl')
    """
    print(f"⚠️ OddsTrader: Scraper disabled (requires JavaScript rendering not available on Streamlit Cloud)")
    print(f"   Using OddsShark and CBS Sports for consensus data instead")
    return

    # DISABLED CODE BELOW - Kept for reference
    # 1. Check if sport is in season
    if not SportConfig.is_in_season(sport):
        print(f"📡 OddsTrader: Skipping {sport.upper()} - out of season")
        return

    # 2. Map sport key to OddsTrader URL path
    sport_url_map = {
        "americanfootball_nfl": "nfl",
        "americanfootball_ncaaf": "ncaa-college-football",
        "basketball_nba": "nba",
        "basketball_ncaab": "ncaa-college-basketball",
        "icehockey_nhl": "nhl",
    }

    sport_path = sport_url_map.get(sport)
    if not sport_path:
        print(f"📡 OddsTrader: No URL mapping for {sport}")
        return

    url = f"https://www.oddstrader.com/{sport_path}/picks/"
    sport_name_upper = SportConfig.get_sport_name(sport)

    print(f"📡 OddsTrader: Fetching {sport_name_upper} picks from {url}...")

    try:
        # Use pure BeautifulSoup (no JavaScript rendering - works on Streamlit Cloud)
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all bet containers with star ratings
        # Based on your HTML: div.wrapper-irK6Y contains individual bets
        bet_containers = soup.select("div.wrapper-irK6Y")
        print(f"🔍 OddsTrader: Found {len(bet_containers)} bet containers")

        scraped_count = 0

        # Group bets by game (each game has multiple bet options)
        # Find all game containers: div.content-JBK0_ contains participants + bets
        game_containers = soup.select("div.content-JBK0_")
        print(f"🎮 OddsTrader: Found {len(game_containers)} games")

        for game_container in game_containers:
            try:
                # Extract team names from participants
                participants = game_container.select(
                    "div.participant-JUvdP span.Textstyles__StyledText-sc-qzd0it-0.jZXjOG")
                if len(participants) < 2:
                    continue

                away_team = normalize_team_name(
                    participants[0].get_text(strip=True), sport)
                home_team = normalize_team_name(
                    participants[1].get_text(strip=True), sport)

                if not away_team or not home_team:
                    continue

                game_id = create_game_id(
                    away_team, home_team, sport_name_upper, target_date)

                # Extract all bet options for this game
                bet_wrappers = game_container.select("div.wrapper-irK6Y")

                for bet_wrapper in bet_wrappers:
                    try:
                        # Get star rating (count filled stars)
                        filled_stars = bet_wrapper.select("i.ot-full-star")
                        star_rating = len(filled_stars)

                        # Only process 3-4 star picks (as requested)
                        if star_rating < 3 or star_rating > 4:
                            continue

                        # Extract market type (Spread, Total, etc.)
                        market_label = bet_wrapper.select_one(
                            "div.label span.Textstyles__StyledText-sc-qzd0it-0.gLWpWd")
                        if not market_label:
                            continue

                        market = market_label.get_text(strip=True).lower()

                        # Extract line and odds from button
                        line_elem = bet_wrapper.select_one(
                            "div.line-kJ08c span.Textstyles__StyledText-sc-qzd0it-0.lehILx")
                        odds_elem = bet_wrapper.select_one(
                            "div.line-kJ08c span.Textstyles__StyledText-sc-qzd0it-0.fMpABJ")

                        if not line_elem:
                            continue

                        line = line_elem.get_text(strip=True)
                        odds_value = odds_elem.get_text(
                            strip=True) if odds_elem else "N/A"

                        # Determine which team is being picked
                        # For spread: +6½ means away team, -6½ means home team
                        # For total: u49 means under, o49 means over
                        if market == "spread":
                            team_pick = away_team if "+" in line else home_team
                        elif market == "total":
                            # Totals apply to both teams
                            team_pick = f"{away_team} vs {home_team}"
                        else:
                            team_pick = away_team  # Default to away team

                        # Store in database
                        data = {
                            "market": market,
                            "line": line,
                            "odds": odds_value,
                            "star_rating": star_rating,
                            "confidence": "high" if star_rating >= 4 else "medium"
                        }

                        insert_context(
                            category="expert_consensus",
                            context_type="oddstrader_pick",
                            game_id=game_id,
                            match_date=target_date,
                            sport=sport_name_upper,
                            team_pick=team_pick,
                            data=data,
                            source="oddstrader"
                        )

                        scraped_count += 1

                    except Exception:
                        continue

            except Exception:
                continue

        print(
            f"✅ OddsTrader: Scraped {scraped_count} picks (3-4 stars) for {sport_name_upper}")

    except Exception as e:
        print(f"❌ OddsTrader: Error scraping {sport_name_upper}: {e}")


def scrape_cbs_expert_picks(target_date: str, sport: str):
    """
    Scrapes CBS Sports expert picks (spread and total only).
    Uses the new 2025 HTML structure with team abbreviations.

    Args:
        target_date: Target date for grouping (YYYY-MM-DD)
        sport: Sport key (e.g., 'americanfootball_nfl')
    """
    # 1. Check if sport is in season
    if not SportConfig.is_in_season(sport):
        print(f"📡 CBS Sports: Skipping {sport.upper()} - out of season")
        return

    # 2. Map sport key to CBS URL path
    sport_url_map = {
        "americanfootball_nfl": "nfl/picks/experts/",
        "americanfootball_ncaaf": "college-football/picks/experts/",
        "basketball_nba": "nba/expert-picks/",
        "icehockey_nhl": "nhl/expert-picks/",
        # NCAAB doesn't have expert picks page yet on CBS
    }

    sport_path = sport_url_map.get(sport)
    if not sport_path:
        print(f"📡 CBS Sports: No expert picks page for {sport}")
        return

    url = f"https://www.cbssports.com/{sport_path}"
    sport_name_upper = SportConfig.get_sport_name(sport)

    # Map team abbreviations to full names for normalization
    # CBS uses 3-letter abbreviations (TOR, IND, CLE, etc.)
    nba_abbrev_map = {
        "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte",
        "CHI": "Chicago", "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver",
        "DET": "Detroit", "GS": "Golden State", "HOU": "Houston", "IND": "Indiana",
        "LAC": "LA Clippers", "LAL": "LA Lakers", "MEM": "Memphis", "MIA": "Miami",
        "MIL": "Milwaukee", "MIN": "Minnesota", "NO": "New Orleans", "NY": "New York",
        "OKC": "Oklahoma City", "ORL": "Orlando", "PHI": "Philadelphia", "PHX": "Phoenix",
        "POR": "Portland", "SAC": "Sacramento", "SA": "San Antonio", "TOR": "Toronto",
        "UTA": "Utah", "WAS": "Washington"
    }

    print(
        f"📡 CBS Sports: Fetching {sport_name_upper} expert picks from {url}...")

    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all expert picks columns (one per game)
        expert_picks_cols = soup.select("div.expert-picks-col")
        print(
            f"🔍 CBS Sports: Found {len(expert_picks_cols)} expert pick columns")

        scraped_count = 0

        # Process each expert picks column
        for expert_picks_col in expert_picks_cols:
            try:
                # Find the parent container to get game info
                # The preview link is typically 2 levels up from expert-picks-col
                parent_container = expert_picks_col.find_parent(
                    "div")  # picks-td
                if parent_container:
                    parent_container = parent_container.find_parent(
                        "div")  # row container

                if not parent_container:
                    continue

                # Look for preview link to extract team abbreviations
                # Format: /nba/gametracker/preview/NBA_20251119_TOR@PHI/
                preview_link = parent_container.find(
                    "a", href=lambda h: h and "gametracker/preview" in h)
                if not preview_link:
                    continue

                href = preview_link.get("href", "")
                # Extract game ID from URL: NBA_20251119_TOR@PHI
                import re
                game_match = re.search(
                    r'NBA_\d{8}_([A-Z]{2,3})@([A-Z]{2,3})', href)
                if not game_match:
                    continue

                away_abbrev = game_match.group(1)
                home_abbrev = game_match.group(2)

                # Map abbreviations to full team names
                away_team_name = nba_abbrev_map.get(away_abbrev)
                home_team_name = nba_abbrev_map.get(home_abbrev)

                if not away_team_name or not home_team_name:
                    print(
                        f"⚠️ CBS Sports: Unknown team abbreviations: {away_abbrev}, {home_abbrev}")
                    continue

                # Normalize team names
                away_team = normalize_team_name(
                    away_team_name, sport_name_upper)
                home_team = normalize_team_name(
                    home_team_name, sport_name_upper)

                # Create game_id
                game_id = create_game_id(
                    away_team, home_team, sport_name_upper, target_date)

                # Extract spread pick
                spread_div = expert_picks_col.select_one("div.expert-spread")
                spread_pick = None
                if spread_div:
                    # Get text content and parse
                    spread_text = spread_div.get_text(strip=True)
                    # Format: "TOR-2.5" or "IND+1.5"
                    # Extract team abbreviation and line
                    import re
                    spread_match = re.search(
                        r'([A-Z]{2,3})\s*([-+][\d.]+)', spread_text)
                    if spread_match:
                        team_abbrev = spread_match.group(1)
                        line = spread_match.group(2)

                        # Map abbreviation to full team name
                        team_name = nba_abbrev_map.get(team_abbrev)
                        if team_name:
                            # Normalize to match our game_id format
                            team_normalized = normalize_team_name(
                                team_name, sport_name_upper)
                            spread_pick = {
                                "market": "spread",
                                "team": team_normalized,
                                "line": line
                            }

                # Extract total pick
                total_div = expert_picks_col.select_one("div.expert-ou")
                total_pick = None
                if total_div:
                    # Get text content and parse
                    total_text = total_div.get_text(strip=True)
                    # Format: "U233.5" or "O232.5"
                    total_match = re.search(r'([OU])([\d.]+)', total_text)
                    if total_match:
                        direction = "over" if total_match.group(
                            1) == "O" else "under"
                        line = total_match.group(2)
                        total_pick = {
                            "market": "total",
                            "direction": direction,
                            "line": line
                        }

                # Store picks in database
                if spread_pick:
                    insert_context(
                        category="expert_consensus",
                        context_type="cbs_expert_pick",
                        game_id=game_id,
                        match_date=target_date,
                        sport=sport_name_upper,
                        team_pick=spread_pick["team"],
                        data=spread_pick,
                        source="cbs_sports"
                    )
                    scraped_count += 1

                if total_pick:
                    insert_context(
                        category="expert_consensus",
                        context_type="cbs_expert_pick",
                        game_id=game_id,
                        match_date=target_date,
                        sport=sport_name_upper,
                        team_pick=None,  # Total picks don't have a team
                        data=total_pick,
                        source="cbs_sports"
                    )
                    scraped_count += 1

            except Exception as e:
                print(f"⚠️ CBS Sports: Error processing game: {e}")
                continue

        print(
            f"✅ CBS Sports: Stored {scraped_count} consensus picks for {sport_name_upper}")

    except Exception as e:
        print(f"❌ CBS Sports: Failed to scrape {sport_name_upper}: {e}")


def run_scrapers(target_date: str, sport: str):
    """Entrypoint for scraping multiple sources for a single sport."""
    scrape_oddsshark_consensus(target_date, sport)
    scrape_oddstrader_picks(target_date, sport)
    scrape_cbs_expert_picks(target_date, sport)
