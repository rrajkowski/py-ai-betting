import os
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
import requests
from datetime import datetime, timedelta, timezone

# Updated imports to include all necessary functions for metrics and auto-refresh
from app.db import (
    get_most_recent_pick_timestamp,
    list_ai_picks,
    init_ai_picks,
    fetch_performance_summary,
    get_unsettled_picks,
    update_pick_result,
)
from app.utils.db import get_db, init_prompt_context_db
from app.utils.context_builder import create_super_prompt_payload
from app.utils.scraper import run_scrapers
from app.utils.kalshi_api import fetch_kalshi_consensus
from app.auth import add_auth_to_page, is_admin
from app.ai_picks import (
    fetch_scores,
    update_ai_pick_results,
    generate_ai_picks,  # Make sure to import generate_ai_picks
    fetch_historical_nfl,
    fetch_historical_ncaaf,
    # fetch_historical_mlb,  # Season over
    fetch_historical_ncaab,
    fetch_historical_nba,
    fetch_historical_nhl
)

# -----------------------------
# Authentication & Paywall
# -----------------------------
# Protect this page with authentication and subscription check
add_auth_to_page()

# --- INITIALIZATION ---
# Run at import to guarantee schemas are correct
init_ai_picks()
init_prompt_context_db()  # NEW: Initialize the new prompt context table

# Only show Maintenance menu for admin users
if is_admin():
    st.sidebar.markdown("### ⚙️ Maintenance")
    if st.sidebar.button("🔁 Update Pick Results"):
        update_ai_pick_results()
        st.success("RAGE Sports Picks updated from live scores!")

    if st.sidebar.button("🧹 Clean Up Picks"):
        with st.spinner("Cleaning up database..."):
            from scripts.cleanup_picks import main as cleanup_main
            import io
            import sys

            # Capture output from cleanup script
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                cleanup_main()
                output = buffer.getvalue()
                sys.stdout = old_stdout

                # Show output in success message
                st.success("Database cleanup complete!")
                with st.expander("📋 Cleanup Details"):
                    st.code(output)
            except Exception as e:
                sys.stdout = old_stdout
                st.error(f"Cleanup failed: {e}")

# Set the desired local timezone for display (PST/PDT)
# Use 'America/Los_Angeles' for PST/PDT to handle daylight savings automatically
LOCAL_TZ_NAME = 'America/Los_Angeles'


# --- Initial Check and Result Update on Page Load (NEW) ---
# NOTE: This logic assumes fetch_scores is available to the refresh_bet_results helper.
def check_if_pick_won(pick, home_score, away_score):
    """
    Determines if a single pick (H2H, Spread, or Total) won, lost, or pushed.
    Returns 'Win', 'Loss', or 'Push'.
    """
    # Helper function logic from previous step (included for completeness)

    # Check if scores are defined
    if home_score is None or away_score is None:
        return 'Pending'

    if pick['market'] == 'h2h':
        if home_score > away_score:
            winner = pick['game'].split(' @ ')[1]  # Home team
        elif away_score > home_score:
            winner = pick['game'].split(' @ ')[0]  # Away team
        else:
            return 'Push'

        return 'Win' if pick['pick'] == winner else 'Loss'

    elif pick['market'] == 'spreads':
        line = pick.get('line')
        if line is None:
            return 'Pending'

        # Determine team scores
        away_team = pick['game'].split(' @ ')[0]
        home_team = pick['game'].split(' @ ')[1]

        # Calculate score differential based on who the bet is on (pick)
        if pick['pick'] == home_team:
            score_diff = home_score - away_score
        elif pick['pick'] == away_team:
            score_diff = away_score - home_score
        else:
            return 'Loss'  # Invalid pick team name

        if score_diff > line:
            return 'Win'
        elif score_diff < line:
            return 'Loss'
        else:
            return 'Push'

    elif pick['market'] == 'totals':
        line = pick.get('line')
        if line is None:
            return 'Pending'

        total_score = home_score + away_score

        if pick['pick'] == 'Over':
            if total_score > line:
                return 'Win'
            elif total_score < line:
                return 'Loss'
            else:
                return 'Push'
        elif pick['pick'] == 'Under':
            if total_score < line:
                return 'Win'
            elif total_score > line:
                return 'Loss'
            else:
                return 'Push'

    return 'Pending'


def refresh_bet_results():
    """
    Fetches unsettled picks, retrieves live scores for completed games,
    calculates the result, and updates the database.
    """

    unsettled_picks = get_unsettled_picks()
    if not unsettled_picks:
        return 0, 0

    # Group picks by sport to minimize API calls
    sports_to_fetch = {}
    for pick in unsettled_picks:
        sport = pick['sport']

        if sport == 'NFL':
            sport_key = 'americanfootball_nfl'
        elif sport == 'NCAAF':
            sport_key = 'americanfootball_ncaaf'
        # elif sport == 'MLB':  # Season over
        #     sport_key = 'baseball_mlb'
        elif sport == 'NCAAB':
            sport_key = 'basketball_ncaab'
        elif sport == 'NBA':
            sport_key = 'basketball_nba'
        elif sport == 'NHL':
            sport_key = 'icehockey_nhl'
        else:
            continue

        if sport_key not in sports_to_fetch:
            sports_to_fetch[sport_key] = set()

        sports_to_fetch[sport_key].add(pick['game'])

    updated_count = 0
    failed_count = 0

    # 1. Fetch scores for each required sport
    for sport_key in sports_to_fetch.keys():
        scores_data = []
        try:
            # Enforce the daysFrom=2 limit due to API constraints.
            scores_data = fetch_scores(sport=sport_key, days_from=1)
        except requests.exceptions.HTTPError as e:
            # Handle the 422 Client Error gracefully, assuming the sport data stream is closed.
            if e.response.status_code == 422:
                st.warning(
                    f"Skipping result refresh for {sport_key.split('_')[-1].upper()}: API stream is likely closed (422 Error).")
                continue  # Skip processing this sport
            else:
                st.error(f"Failed to fetch scores for {sport_key}: {e}")
                failed_count += 1
                continue
        except Exception as e:
            st.error(
                f"An unexpected error occurred fetching scores for {sport_key}: {e}")
            failed_count += 1
            continue

        game_score_map = {}
        for game in scores_data:
            if game.get('completed', False):
                game_id = f"{game.get('away_team')} @ {game.get('home_team')}"

                # 1. Extract and standardize date (YYYY-MM-DD)
                game_date = game.get('commence_time', '')[:10]

                # 2. Safely extract scores
                home_score = next((s['score'] for s in game.get(
                    'scores', []) if s['name'] == game['home_team']), None)
                away_score = next((s['score'] for s in game.get(
                    'scores', []) if s['name'] == game['away_team']), None)

                try:
                    home_score = int(
                        home_score) if home_score is not None else None
                    away_score = int(
                        away_score) if away_score is not None else None

                    if home_score is not None and away_score is not None:
                        # Store game scores AND the unique date
                        game_score_map[game_id] = {
                            'home': home_score,
                            'away': away_score,
                            'date': game_date
                        }
                except ValueError:
                    continue

        # 2. Iterate through unsettled picks and update results
        current_sport_name = sport_key.split('_')[-1].upper()
        for pick in [p for p in unsettled_picks if p['sport'] == current_sport_name]:
            # --- Safely skip picks with a NULL date to prevent crash ---
            if not pick['date']:
                continue

            game_id = pick['game']
            pick_date = pick['date'][:10]

            if game_id in game_score_map:
                scores = game_score_map[game_id]
                if scores['date'] == pick_date:
                    result = check_if_pick_won(
                        pick, scores['home'], scores['away'])
                    if result != 'Pending':
                        update_pick_result(pick['id'], result)
                        updated_count += 1

    return updated_count, failed_count


updated_on_load, _ = refresh_bet_results()
if updated_on_load > 0:
    st.toast(f"Updated {updated_on_load} picks with game results!", icon="✅")


# --- Page Configuration & Title ---
st.set_page_config(page_title="🤖 AI Daily Picks", layout="wide")
st.title("🤖 AI Daily Picks")
st.markdown(
    "Click a button to generate AI-recommended bets for that sport. Picks are generated once per day.")

# --- Initialize Session State ---
# This is crucial for making new picks appear instantly.
if 'generated_picks' not in st.session_state:
    st.session_state.generated_picks = None

# Initialize state for metric display filter
if 'metric_sport' not in st.session_state:
    st.session_state.metric_sport = "NFL"  # Default to NFL metrics

# ----------------------------------------------------
# Function to get sport-specific performance summary
# ----------------------------------------------------


def get_sport_summary(sport_name):
    """Returns W/L/P and units for a specific sport."""
    conn = get_db()
    cur = conn.cursor()

    query = """
    SELECT
        SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) AS total_wins,
        SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) AS total_losses,
        SUM(CASE WHEN result = 'Push' THEN 1 ELSE 0 END) AS total_pushes,
        SUM(
            CASE
                WHEN result = 'Win' AND odds_american > 0 THEN (odds_american / 100.0)
                WHEN result = 'Win' AND odds_american < 0 THEN (100.0 / ABS(odds_american))
                WHEN result = 'Loss' THEN -1.0
                ELSE 0
            END
        ) AS net_units
    FROM ai_picks
    WHERE sport = ? AND result IN ('Win', 'Loss', 'Push');
    """
    cur.execute(query, (sport_name,))
    row = cur.fetchone()
    conn.close()

    if not row or row[0] is None:
        return {"wins": 0, "losses": 0, "pushes": 0, "units": 0.0}

    return {
        "wins": row[0] or 0,
        "losses": row[1] or 0,
        "pushes": row[2] or 0,
        "units": round(row[3] or 0.0, 2),
    }


# Aggregate results for ALL sports


def fetch_all_sports_summary():
    """
    Calculates aggregate W/L/P and units across all sports.
    Units calculation: Win = profit based on odds, Loss = -1 unit, Push = 0 units.
    """
    conn = get_db()
    cur = conn.cursor()

    query = """
    SELECT
        SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) AS total_wins,
        SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) AS total_losses,
        SUM(CASE WHEN result = 'Push' THEN 1 ELSE 0 END) AS total_pushes,
        SUM(
            CASE
                WHEN result = 'Win' AND odds_american > 0 THEN (odds_american / 100.0)
                WHEN result = 'Win' AND odds_american < 0 THEN (100.0 / ABS(odds_american))
                WHEN result = 'Loss' THEN -1.0
                ELSE 0
            END
        ) AS net_units
    FROM ai_picks
    WHERE result IN ('Win', 'Loss', 'Push');
    """
    cur.execute(query)
    row = cur.fetchone()
    conn.close()

    if not row:
        return {"wins": 0, "losses": 0, "pushes": 0, "units": 0.0}

    return {
        "wins": row[0] or 0,
        "losses": row[1] or 0,
        "pushes": row[2] or 0,
        "units": round(row[3] or 0.0, 2),
    }


# --- GLOBAL PERFORMANCE METRICS DISPLAY (MOVED TO TOP) ---
summary = fetch_all_sports_summary()
wl_summary = f"{summary['wins']}-{summary['losses']}-{summary['pushes']}"
units_color = "#22c55e" if summary['units'] >= 0 else "#ef4444"

# Header with inline stats
st.markdown(
    f"""
    <div style='display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;'>
        <h2 style='margin: 0; padding: 0;'>🏆 Historical Performance</h2>
        <div style='display: flex; gap: 24px; font-size: 15px;'>
            <div><b>W/L/P:</b> {wl_summary}</div>
            <div><b>Units:</b> <span style='color: {units_color}; font-weight: bold;'>{summary['units']:+.2f}u</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# Main AI Pick Generation Logic
# -----------------------------


def run_ai_picks(sport_key, sport_name):
    """
    Main function to generate AI picks, with corrected timezone and time-limit handling.
    """
    # Use today's date as starting point - context builder will fetch games for next 3 days
    now_utc = datetime.now(timezone.utc)
    target_date = now_utc.strftime('%Y-%m-%d')
    last_pick_time = get_most_recent_pick_timestamp(sport_name)

    if last_pick_time:
        if last_pick_time > now_utc:
            st.warning(
                "Future-dated pick found. Ignoring time limit for this run.")
        else:
            if last_pick_time.tzinfo is None:
                last_pick_time = last_pick_time.replace(tzinfo=timezone.utc)

            # --- Use an environment variable for reliable local detection ---
            environment = os.getenv("ENVIRONMENT", "production")

            if environment == "development":
                wait_duration = timedelta(minutes=1)
            else:
                wait_duration = timedelta(hours=12)

            next_run_time = last_pick_time + wait_duration
            time_to_wait = next_run_time - now_utc

            if time_to_wait > timedelta(0):
                hours, remainder = divmod(time_to_wait.total_seconds(), 3600)
                minutes, _ = divmod(remainder, 60)
                local_tz = ZoneInfo(LOCAL_TZ_NAME)
                last_pick_local = last_pick_time.astimezone(local_tz)
                st.info(f"Picks for {sport_name} were generated recently. Last generated: {last_pick_local.strftime('%Y-%m-%d %I:%M %p %Z')}. Please wait {int(hours)} hours and {int(minutes)} minutes before running again. ⏳")
                return
    # --- UI Status Indicators and Data Fetching ---
    status_cols = st.columns(3)
    status_placeholders = {
        'scrape': status_cols[0].empty(),
        'api': status_cols[1].empty(),
        'context': status_cols[2].empty(),
    }

    with st.spinner("Step 1: Fetching latest data..."):
        status_placeholders['scrape'].info("🟡 Fetching Expert Consensus...")
        run_scrapers(target_date, sport_key)
        status_placeholders['scrape'].success("✅ Expert Consensus Saved.")
        status_placeholders['api'].info("🟡 Fetching Public Consensus...")
        fetch_kalshi_consensus(sport_key, target_date)
        status_placeholders['api'].success("✅ Public Consensus Saved.")

    with st.spinner("Step 2: Building AI context..."):
        status_placeholders['context'].info("🟡 Building LLM Context...")
        context_payload = create_super_prompt_payload(target_date, sport_key)
        status_placeholders['context'].success(
            f"✅ Context Built ({len(context_payload.get('games', []))} Games)")

    with st.spinner(f"Step 3: AI is analyzing {sport_name} games..."):
        from app.ai_picks import fetch_odds

        raw_odds = fetch_odds(sport_key)

        if not raw_odds:
            st.warning("No upcoming games with odds were found.")
            return

        # Time-based filtering with progressive expansion
        # Start with 12 hours, expand to 24h, then sport-specific limits
        now_utc = datetime.now(timezone.utc)

        # Sport-specific time windows (in hours)
        time_windows = {
            "basketball_nba": [12, 24],      # NBA: Try 12h first, then 24h
            "basketball_ncaab": [12, 24],    # NCAAB: Try 12h first, then 24h
            # NFL: 1 day, 2 days, 3 days (Thu/Sun/Mon)
            "americanfootball_nfl": [24, 48, 72],
            "americanfootball_ncaaf": [24, 48],    # NCAAF: 1 day, 2 days
            "icehockey_nhl": [12, 24],       # NHL: Try 12h first, then 24h
        }

        windows = time_windows.get(sport_key, [12, 24])  # Default: 12h, 24h
        min_markets_threshold = 15  # Minimum markets needed before stopping expansion

        normalized_odds = []
        total_markets = 0
        filtered_markets = 0
        time_window_used = 0
        games_in_window = 0

        # Try each time window until we have enough markets
        for i, hours in enumerate(windows):
            max_time = now_utc + timedelta(hours=hours)
            temp_normalized_odds = []
            temp_total_markets = 0
            temp_filtered_markets = 0
            temp_games_in_window = 0

            for row in raw_odds:
                # Parse game time
                game_time_str = row.get('commence_time', '')
                try:
                    game_time = datetime.fromisoformat(
                        game_time_str.replace('Z', '+00:00'))
                except:
                    continue

                # Skip games outside time window
                if game_time > max_time:
                    continue

                temp_games_in_window += 1

                bookmaker = next((b for b in row.get("bookmakers", [])
                                 if b["key"] == "draftkings"), None)
                if not bookmaker:
                    continue

                details = {"game": f"{row['away_team']} @ {row['home_team']}",
                           "sport": sport_name, "commence_time": row.get('commence_time')}

                for market in bookmaker.get("markets", []):
                    market_key = market["key"]
                    outcomes = market.get("outcomes", [])

                    # Count total markets
                    temp_total_markets += len(outcomes)

                    # For h2h (moneyline), filter out extreme odds
                    if market_key == "h2h":
                        # Only include if BOTH sides have acceptable odds
                        if len(outcomes) == 2:
                            odds1 = outcomes[0].get("price", 0)
                            odds2 = outcomes[1].get("price", 0)

                            # Skip if either side is outside -150 to +150 range
                            if odds1 < -150 or odds1 > 150 or odds2 < -150 or odds2 > 150:
                                continue  # Skip this h2h market

                    # Include all spreads and totals (they're almost always ~-110)
                    # Include h2h only if it passed the filter above
                    for outcome in outcomes:
                        bet = details.copy()
                        bet.update({"market": market_key, "pick": outcome.get(
                            "name"), "odds_american": outcome.get("price"), "line": outcome.get("point")})
                        temp_normalized_odds.append(bet)
                        temp_filtered_markets += 1

            # Update results
            normalized_odds = temp_normalized_odds
            total_markets = temp_total_markets
            filtered_markets = temp_filtered_markets
            games_in_window = temp_games_in_window
            time_window_used = hours

            # Stop if we have enough markets OR this is the last window
            is_last_window = (i == len(windows) - 1)
            if filtered_markets >= min_markets_threshold or is_last_window:
                break

        if not normalized_odds:
            st.warning(
                f"No {sport_name} markets found with acceptable odds. All h2h markets have extreme mismatches and no spreads/totals available.")
            return

        st.info(
            f"📊 Found {filtered_markets} competitive {sport_name} markets from {games_in_window} games in next {time_window_used}h (filtered from {total_markets} total markets)")

        history_team = raw_odds[0]['home_team']
        history_map = {"americanfootball_ncaaf": fetch_historical_ncaaf, "americanfootball_nfl": fetch_historical_nfl,
                       # "baseball_mlb": fetch_historical_mlb,  # Season over
                       "basketball_ncaab": fetch_historical_ncaab, "basketball_nba": fetch_historical_nba,
                       "icehockey_nhl": fetch_historical_nhl}
        history = history_map.get(sport_key, lambda x: [])(history_team)

        odds_df = pd.DataFrame(normalized_odds)
        picks = generate_ai_picks(
            odds_df, history, sport=sport_name, context_payload=context_payload)
        st.session_state.generated_picks = picks

    for placeholder in status_placeholders.values():
        placeholder.empty()


# --- UI Controls (Buttons) with Sport Stats ---
st.header("Generate New Picks")

# Get stats for each sport
nfl_stats = get_sport_summary("NFL")
ncaaf_stats = get_sport_summary("NCAAF")
ncaab_stats = get_sport_summary("NCAAB")
nba_stats = get_sport_summary("NBA")
nhl_stats = get_sport_summary("NHL")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("🏈 Generate NFL Picks", use_container_width=True):
        st.session_state.generated_picks = None
        run_ai_picks("americanfootball_nfl", "NFL")
    units_color = "#22c55e" if nfl_stats['units'] >= 0 else "#ef4444"
    st.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #6b7280; margin-top: -8px;'>"
        f"{nfl_stats['wins']}-{nfl_stats['losses']}-{nfl_stats['pushes']} • "
        f"<span style='color: {units_color}; font-weight: 600;'>{nfl_stats['units']:+.1f}u</span>"
        f"</div>",
        unsafe_allow_html=True
    )

with col2:
    if st.button("🎓 Generate NCAAF Picks", use_container_width=True):
        st.session_state.generated_picks = None
        run_ai_picks("americanfootball_ncaaf", "NCAAF")
    units_color = "#22c55e" if ncaaf_stats['units'] >= 0 else "#ef4444"
    st.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #6b7280; margin-top: -8px;'>"
        f"{ncaaf_stats['wins']}-{ncaaf_stats['losses']}-{ncaaf_stats['pushes']} • "
        f"<span style='color: {units_color}; font-weight: 600;'>{ncaaf_stats['units']:+.1f}u</span>"
        f"</div>",
        unsafe_allow_html=True
    )

with col3:
    if st.button("🏀 Generate NCAAB Picks", use_container_width=True):
        st.session_state.generated_picks = None
        run_ai_picks("basketball_ncaab", "NCAAB")
    units_color = "#22c55e" if ncaab_stats['units'] >= 0 else "#ef4444"
    st.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #6b7280; margin-top: -8px;'>"
        f"{ncaab_stats['wins']}-{ncaab_stats['losses']}-{ncaab_stats['pushes']} • "
        f"<span style='color: {units_color}; font-weight: 600;'>{ncaab_stats['units']:+.1f}u</span>"
        f"</div>",
        unsafe_allow_html=True
    )

with col4:
    if st.button("🏀 Generate NBA Picks", use_container_width=True):
        st.session_state.generated_picks = None
        run_ai_picks("basketball_nba", "NBA")
    units_color = "#22c55e" if nba_stats['units'] >= 0 else "#ef4444"
    st.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #6b7280; margin-top: -8px;'>"
        f"{nba_stats['wins']}-{nba_stats['losses']}-{nba_stats['pushes']} • "
        f"<span style='color: {units_color}; font-weight: 600;'>{nba_stats['units']:+.1f}u</span>"
        f"</div>",
        unsafe_allow_html=True
    )

with col5:
    if st.button("🏒 Generate NHL Picks", use_container_width=True):
        st.session_state.generated_picks = None
        run_ai_picks("icehockey_nhl", "NHL")
    units_color = "#22c55e" if nhl_stats['units'] >= 0 else "#ef4444"
    st.markdown(
        f"<div style='text-align: center; font-size: 12px; color: #6b7280; margin-top: -8px;'>"
        f"{nhl_stats['wins']}-{nhl_stats['losses']}-{nhl_stats['pushes']} • "
        f"<span style='color: {units_color}; font-weight: 600;'>{nhl_stats['units']:+.1f}u</span>"
        f"</div>",
        unsafe_allow_html=True
    )


# --- Display Newly Generated Picks (with Error Handling) ---
if st.session_state.generated_picks:
    picks = st.session_state.generated_picks
    st.subheader(f"Today's Top {len(picks)} AI Picks")

    if not picks:
        st.info("The AI found no high-value picks for the upcoming games.")
    else:
        # Use a maximum of 3 columns for display, regardless of the number of picks
        num_cols = min(len(picks), 3)
        cols = st.columns(num_cols)

        for i, pick in enumerate(picks):
            with cols[i % 3]:
                with st.container(border=True):
                    # --- Check if 'pick' is a dictionary before processing ---
                    if isinstance(pick, dict):
                        try:
                            score = int(pick.get('confidence', 1))
                            stars = "⭐" * max(1, min(5, score))
                        except (ValueError, TypeError):
                            stars = "⭐"

                        st.markdown(f"""
                        **Pick #{i+1}**
                        - 🏟️ **Game:** *{pick.get('game','?')}*
                        - 👉 **Pick:** **{pick.get('pick','?')}** ({pick.get('market','?')})
                        - 📏 **Line:** {pick.get('line','-')}
                        - 💵 **Odds:** {pick.get('odds_american','?')}
                        - ⭐ **Confidence:** {stars}
                        - 💡 **Reasoning:** {pick.get('reasoning','')}
                        """)
                    else:
                        # If 'pick' is just a string, display it directly
                        st.markdown(f"**Pick #{i+1}**\n- {str(pick)}")

# --- AI Picks History Table ---
st.header("📜 RAGE Sports Picks History")
ai_picks_history = list_ai_picks()

if ai_picks_history:
    df = pd.DataFrame(ai_picks_history).sort_values(
        by=["date", "id"], ascending=False, na_position="last"
    )

    # --- Filter out completed picks (win/loss/push) ---
    completed_statuses = {"win", "loss", "push"}
    df = df[~df["result"].astype(str).str.lower().isin(completed_statuses)]

    # --- NEW: Filter out low-confidence (1–2 star) picks ---
    df["confidence_numeric"] = pd.to_numeric(
        df["confidence"], errors="coerce").fillna(0)
    df = df[df["confidence_numeric"] >= 3]

    # --- Sort descending by confidence ---
    df.sort_values(by="confidence_numeric", ascending=False, inplace=True)

    # --- Convert confidence to stars for display ---
    def score_to_stars(score):
        try:
            return "⭐" * max(1, min(5, int(score)))
        except (ValueError, TypeError):
            return "⭐"

    df["Confidence (Stars)"] = df["confidence_numeric"].apply(score_to_stars)

    # --- Define and reorder display columns ---
    display_cols = [
        "date",
        "sport",
        "game",
        "pick",
        "market",
        "line",
        "odds_american",
        "result",
        "Confidence (Stars)",
        "reasoning",
    ]

    df_display = df[display_cols].rename(
        columns={"Confidence (Stars)": "confidence"}
    )

    st.dataframe(df_display, width='stretch', hide_index=True)

else:
    st.info("No AI picks have been saved yet.")
