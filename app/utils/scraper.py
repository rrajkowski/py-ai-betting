import asyncio
from playwright.async_api import async_playwright
from app.utils.db import insert_context
from datetime import datetime, timezone


async def safe_inner_text(locator, default=None, timeout=10000):
    try:
        return await locator.inner_text(timeout=timeout)
    except Exception:
        return default


async def scrape_oddsshark_consensus(target_date: str, sport: str):
    """
    Scrapes OddsShark's computer picks page for expert consensus data for a single sport.
    """
    # Map internal sport key to OddsShark URL segment (e.g., americanfootball_nfl -> nfl)
    sport_segment = sport.split('_')[-1].lower()

    # URL construction using the specific sport segment
    url = f"https://www.oddsshark.com/{sport_segment}/computer-picks"
    print(f"📡 Scraper starting for OddsShark on {sport.upper()} at {url}...")

    sport_name_upper = sport.split('_')[-1].upper()

    # Timeouts (ms)
    NAV_TIMEOUT = 120000   # navigation / page load
    SEL_TIMEOUT = 60000    # selector waits

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox"]
            )

            # Use a context for better isolation / control
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            # Set default timeouts
            page.set_default_timeout(SEL_TIMEOUT)
            page.set_default_navigation_timeout(NAV_TIMEOUT)

            # Load external page
            await page.goto(url, wait_until="domcontentloaded")

            # Ensure the outer content container is attached
            try:
                await page.wait_for_selector('.computer-picks-content', state="attached")
            except Exception:
                html = await page.content()
                print("⚠️ Could not find .computer-picks-content. Page snippet:")
                print(html[:2000])  # first 2000 chars for debug
                raise

            # Collect all event containers
            game_containers = await page.locator(
                '.computer-picks-content .computer-picks-event-container'
            ).all()

            print(
                f"🔍 Found {len(game_containers)} game containers for {sport_name_upper}.")

            scraped_picks_count = 0

            for index, container in enumerate(game_containers):
                try:
                    # --- 1. Extract Game Data and Date ---
                    event_date_element = await container.locator(
                        '.odds--group__event-container'
                    ).get_attribute('data-event-date')

                    if event_date_element:
                        try:
                            timestamp = int(event_date_element)
                            game_date_utc = datetime.fromtimestamp(
                                timestamp, tz=timezone.utc
                            ).strftime('%Y-%m-%d')
                        except ValueError:
                            game_date_utc = target_date
                    else:
                        game_date_utc = target_date

                    # Team Names
                    teams = []
                    try:
                        team_names_container = container.locator('.team-names')
                        teams_raw = await team_names_container.all_inner_texts()
                        if teams_raw:
                            teams = [t.strip()
                                     for t in teams_raw[0].split('VS') if t.strip()]
                    except Exception:
                        pass

                    if len(teams) < 2:
                        try:
                            matchup_link_text = await container.locator(
                                '.matchup-link'
                            ).inner_text(timeout=3000)
                            if '@' in matchup_link_text:
                                teams = [t.strip()
                                         for t in matchup_link_text.split('@')]
                        except Exception:
                            pass

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

                    # --- 2. Extract Consensus Picks with shorter timeouts ---
                    ml_pick = await safe_inner_text(container.locator('.predicted-score .highlighted-pick'))
                    spread_pick = await safe_inner_text(container.locator('.spread-pick .highlighted-pick'))
                    total_pick = await safe_inner_text(container.locator('.total-pick .highlighted-pick'))

                    # --- 3. Normalize + Insert ---
                    def normalize(val):
                        return val.strip() if val else ""

                    consensus_data = {
                        "game_title": game_title,
                        "ml_pick_raw": normalize(ml_pick),
                        "spread_pick_raw": normalize(spread_pick),
                        "total_pick_raw": normalize(total_pick),
                        "extraction_date": datetime.now(timezone.utc).isoformat()
                    }

                    insert_context(
                        category="storage",
                        context_type="expert_consensus",
                        game_id=game_id,
                        match_date=game_date_utc,
                        sport=sport_name_upper,
                        data=consensus_data,
                        source="oddsshark"
                    )
                    scraped_picks_count += 1

                except Exception as container_e:
                    print(
                        f"⚠️ Could not parse container #{index} on {sport_name_upper}: {container_e}")
                    continue

            print(
                f"✅ Scraper finished. Stored {scraped_picks_count} picks for {sport_name_upper}.")

            await context.close()
            await browser.close()

    except Exception as e:
        print(f"❌ Scrape failed fatally for {sport.upper()} on {url}: {e}")
        raise


def run_scrapers(target_date: str, sport: str):
    """Entrypoint for scraping a single sport."""
    asyncio.run(scrape_oddsshark_consensus(target_date, sport))
