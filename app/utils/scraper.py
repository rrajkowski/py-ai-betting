import requests
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from datetime import datetime, timezone, timedelta
from app.utils.db import insert_context
from app.utils.sport_config import SportConfig
from app.utils.team_mapper import normalize_team_name


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
    Uses requests-html to render JavaScript content.

    Args:
        target_date: Target date for grouping (YYYY-MM-DD)
        sport: Sport key (e.g., 'americanfootball_nfl')
    """
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
    }

    sport_path = sport_url_map.get(sport)
    if not sport_path:
        print(f"📡 OddsTrader: No URL mapping for {sport}")
        return

    url = f"https://www.oddstrader.com/{sport_path}/picks/"
    sport_name_upper = SportConfig.get_sport_name(sport)

    print(f"📡 OddsTrader: Fetching {sport_name_upper} picks from {url}...")

    try:
        # Check if we're in an environment with an event loop (Streamlit issue)
        import asyncio
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            # No event loop - create one for this thread
            asyncio.set_event_loop(asyncio.new_event_loop())

        # Use HTMLSession to render JavaScript
        session = HTMLSession()
        resp = session.get(url, timeout=30)

        print(f"🔄 OddsTrader: Rendering JavaScript (this may take 10-20 seconds)...")
        resp.html.render(timeout=20, sleep=2)  # Wait for JavaScript to load

        soup = BeautifulSoup(resp.html.html, "html.parser")

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

                game_id = f"{sport_name_upper}-{away_team.replace(' ', '')}-vs-{home_team.replace(' ', '')}-{target_date}"

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
    finally:
        # Close the session to free resources
        # Suppress pyppeteer cleanup warnings (harmless)
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                session.close()
        except Exception:
            pass


def scrape_cbs_expert_picks(target_date: str, sport: str):
    """
    Scrapes CBS Sports expert picks (spread and total only).
    Focuses on consensus when 5+ experts agree.

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
        # NCAAB doesn't have expert picks page yet on CBS
    }

    sport_path = sport_url_map.get(sport)
    if not sport_path:
        print(f"📡 CBS Sports: No expert picks page for {sport}")
        return

    url = f"https://www.cbssports.com/{sport_path}"
    sport_name_upper = SportConfig.get_sport_name(sport)

    print(
        f"📡 CBS Sports: Fetching {sport_name_upper} expert picks from {url}...")

    try:
        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        }, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find game rows - CBS uses table structure
        game_rows = soup.select("tr.TableBase-bodyTr")
        print(f"🔍 CBS Sports: Found {len(game_rows)} game rows")

        scraped_count = 0

        # Group buttons by game using gameId from data-config
        import json
        games_dict = {}  # gameId -> list of bet buttons

        for row in game_rows:
            bet_buttons = row.select("button.BetButton")
            for button in bet_buttons:
                data_config = button.get("data-config")
                if not data_config:
                    continue

                try:
                    config = json.loads(data_config)
                    game_id_cbs = config.get("gameId")
                    if game_id_cbs:
                        if game_id_cbs not in games_dict:
                            games_dict[game_id_cbs] = []
                        games_dict[game_id_cbs].append((button, config))
                except:
                    continue

        print(f"🎮 CBS Sports: Found {len(games_dict)} unique games")

        # Process each game
        for game_id_cbs, buttons_configs in games_dict.items():
            try:
                # Extract all picks for this game
                game_bets = []
                teams_found = set()

                for button, config in buttons_configs:
                    button_text = button.select_one("div.BetButton-text")
                    if not button_text:
                        continue

                    pick_text = button_text.get_text(
                        strip=True)  # e.g., "ATL +6.5"
                    market_name = config.get(
                        "marketName", "").lower()  # "Spread" or "Total"

                    game_bets.append({
                        "pick": pick_text,
                        "market": market_name,
                        "line": config.get("line", "")
                    })

                    # Extract team abbreviation
                    pick_parts = pick_text.split()
                    if len(pick_parts) >= 1:
                        team_abbr = pick_parts[0]
                        normalized = normalize_team_name(team_abbr, sport)
                        if normalized:
                            teams_found.add(normalized)

                if not game_bets or len(teams_found) < 2:
                    continue

                # Sort teams alphabetically for consistency
                teams_list = sorted(list(teams_found))
                away_team = teams_list[0]
                home_team = teams_list[1]

                game_id = f"{sport_name_upper}-{away_team.replace(' ', '')}-vs-{home_team.replace(' ', '')}-{target_date}"

                # Count expert consensus for each pick
                # CBS shows multiple expert picks per game - count how many picked each side
                spread_picks = [
                    b for b in game_bets if b["market"] == "spread"]
                total_picks = [
                    b for b in game_bets if "total" in b["market"].lower()]

                # For spread: count picks for each team
                spread_consensus = {}
                for pick in spread_picks:
                    spread_consensus[pick["pick"]] = spread_consensus.get(
                        pick["pick"], 0) + 1

                # For total: count over/under picks
                total_consensus = {}
                for pick in total_picks:
                    total_consensus[pick["pick"]] = total_consensus.get(
                        pick["pick"], 0) + 1

                # Store picks where 5+ experts agree
                for pick_text, count in spread_consensus.items():
                    if count >= 5:
                        # Determine which team
                        team_pick = away_team if away_team[:3].upper(
                        ) in pick_text.upper() else home_team

                        data = {
                            "market": "spread",
                            "line": pick_text,
                            "expert_count": count,
                            "confidence": "high"
                        }

                        insert_context(
                            category="expert_consensus",
                            context_type="cbs_expert_pick",
                            game_id=game_id,
                            match_date=target_date,
                            sport=sport_name_upper,
                            team_pick=team_pick,
                            data=data,
                            source="cbs_sports"
                        )
                        scraped_count += 1

                for pick_text, count in total_consensus.items():
                    if count >= 5:
                        team_pick = f"{away_team} vs {home_team}"

                        data = {
                            "market": "total",
                            "line": pick_text,
                            "expert_count": count,
                            "confidence": "high"
                        }

                        insert_context(
                            category="expert_consensus",
                            context_type="cbs_expert_pick",
                            game_id=game_id,
                            match_date=target_date,
                            sport=sport_name_upper,
                            team_pick=team_pick,
                            data=data,
                            source="cbs_sports"
                        )
                        scraped_count += 1

            except Exception:
                continue

        print(
            f"✅ CBS Sports: Stored {scraped_count} consensus picks for {sport_name_upper}")

    except requests.exceptions.Timeout:
        print(f"❌ CBS Sports timeout for {sport_name_upper}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ CBS Sports HTTP error: {e.response.status_code}")
    except Exception as e:
        print(f"❌ CBS Sports error for {sport_name_upper}: {e}")


def run_scrapers(target_date: str, sport: str):
    """Entrypoint for scraping multiple sources for a single sport."""
    scrape_oddsshark_consensus(target_date, sport)
    scrape_oddstrader_picks(target_date, sport)
    scrape_cbs_expert_picks(target_date, sport)
