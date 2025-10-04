import pandas as pd
import streamlit as st
import pytz
import requests
from datetime import datetime, timedelta
# Updated imports to include all necessary functions for metrics and auto-refresh
from app.db import (
    get_most_recent_pick_timestamp,
    list_ai_picks,
    init_ai_picks,
    fetch_performance_summary,
    get_unsettled_picks,
    update_pick_result,
)
from app.utils.db import init_prompt_context_db
from app.utils.context_builder import create_super_prompt_payload
from app.utils.scraper import run_scrapers
from app.utils.kalshi_api import fetch_kalshi_consensus
from app.ai_picks import (
    fetch_odds,
    fetch_historical_nfl,
    fetch_historical_mlb,
    fetch_historical_ncaaf,
    generate_ai_picks,
    fetch_scores
)


# --- INITIALIZATION ---
# Run at import to guarantee schemas are correct
init_ai_picks()
init_prompt_context_db()  # NEW: Initialize the new prompt context table

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
        elif sport == 'MLB':
            sport_key = 'baseball_mlb'
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
            scores_data = fetch_scores(sport=sport_key, days_from=2)
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
            game_id = pick['game']
            pick_date = pick['date'][:10]  # Extract date from pick's timestamp

            if game_id in game_score_map:
                scores = game_score_map[game_id]

                # CRITICAL: Check for game ID and date match to resolve duplicate games
                if scores['date'] == pick_date:

                    # Calculate Win/Loss/Push
                    result = check_if_pick_won(
                        pick, scores['home'], scores['away'])

                    if result not in ['Pending']:
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
# Function to display performance metrics
# ----------------------------------------------------


def display_performance_metrics(sport_name, col_container):
    """Fetches and displays the performance metrics table by confidence level in the given container."""
    summary = fetch_performance_summary(sport_name)

    with col_container:
        st.subheader(f"{sport_name} Metrics")

        # Define columns for the summary table header
        col_names = st.columns(3)
        col_names[0].markdown('**W/L**')
        col_names[1].markdown('**Conf**')
        col_names[2].markdown('**Units**')
        st.markdown("---")

        # Display rows for each confidence level (2, 3, 4, 5 stars)
        found_metrics = False
        for row in summary:
            found_metrics = True

            try:
                star_rating = int(row['star_rating'])
            except (ValueError, TypeError):
                continue  # Skip if star_rating is invalid

            stars = '⭐' * star_rating
            w_l_record = f"{row['total_wins']}-{row['total_losses']}"
            net_units = row['net_units']

            # Determine color for units
            color = "green" if net_units >= 0 else "red"

            # Display each row using st.columns (3 columns inside the main container column)
            cols = st.columns(3)

            with cols[0]:
                st.markdown(w_l_record)

            with cols[1]:
                st.markdown(stars)

            with cols[2]:
                # Format to two decimal places and apply color
                st.markdown(
                    f"<span style='color: {color}; font-weight: bold;'>{net_units:+.2f}u</span>", unsafe_allow_html=True)

        if not found_metrics:
            st.info("No completed picks found.")


# --- GLOBAL PERFORMANCE METRICS DISPLAY (MOVED TO TOP) ---
st.header("🏆 Historical Performance")
metric_cols = st.columns(3)

# Display metrics for all three sports automatically
display_performance_metrics("NFL", metric_cols[0])
display_performance_metrics("NCAAF", metric_cols[1])
display_performance_metrics("MLB", metric_cols[2])


# -----------------------------
# Main AI Pick Generation Logic
# -----------------------------


def run_ai_picks(sport_key, sport_name):
    # Determine the target analysis date
    # Get today's date in UTC and format as YYYY-MM-DD
    target_date = datetime.now(pytz.utc).strftime('%Y-%m-%d')

    # --- Time Limit Check ---
    last_pick_time = get_most_recent_pick_timestamp(sport_name)
    now_utc = datetime.now(pytz.utc)

    if last_pick_time:
        next_run_time = last_pick_time + timedelta(hours=12)  # 12-hour limit
        # next_run_time = last_pick_time +  timedelta(minutes=1)  # 1min for testing
        time_to_wait = next_run_time - now_utc

        if time_to_wait > timedelta(0):
            hours, remainder = divmod(time_to_wait.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            local_tz = pytz.timezone(LOCAL_TZ_NAME)
            last_pick_local = last_pick_time.astimezone(local_tz)

            st.info(
                f"Picks for {sport_name} were generated today. Last generated: {last_pick_local.strftime('%Y-%m-%d %I:%M %p %Z')}. "
                f"Please wait {int(hours)} hours and {int(minutes)} minutes before running again. ⏳"
            )
            return

    # --- UI Status Indicators Setup (NEW) ---
    status_cols = st.columns(3)
    status_placeholders = {
        'scrape': status_cols[0].empty(),
        'api': status_cols[1].empty(),
        'context': status_cols[2].empty(),
    }

    # 1. Data Acquisition (Scraping/Realtime API)
    with st.spinner("Step 1: Fetching Expert Consensus and Public Data..."):
        # 1a. Expert Consensus (Storage - Scrape)
        status_placeholders['scrape'].info("🟡 Fetching Expert Consensus...")
        # NOTE: run_scrapers now takes the sport_key to filter the scrape
        run_scrapers(target_date, sport_key)
        status_placeholders['scrape'].success("✅ Expert Consensus Data Saved.")

        # 1b. Public Consensus (Realtime - Kalshi API)
        status_placeholders['api'].info("🟡 Fetching Public Consensus...")
        # Placeholder: Assumes insertion
        fetch_kalshi_consensus(sport_key, target_date)
        status_placeholders['api'].success("✅ Public Consensus Data Saved.")

    # 2. Context Aggregation
    status_placeholders['context'].info("🟡 Building LLM Context Payload...")
    # Merge all data sources into a single payload for the LLM
    context_payload = create_super_prompt_payload(
        target_date, sport_key)  # NEW: Passed sport_key
    status_placeholders['context'].success(
        f"✅ Context Built ({len(context_payload.get('games', []))} Games)")

    # --- 4. Model Execution (Existing Logic) ---
    with st.spinner(f"Step 2: AI is analyzing {sport_name} games with {len(context_payload.get('games', []))} context blocks..."):

        raw_odds = fetch_odds(sport_key)

        if not raw_odds:
            st.warning("No upcoming games with odds were found.")
            return

        normalized_odds = []
        for row in raw_odds:
            bookmaker = next((b for b in row.get("bookmakers", [])
                             if b["key"] == "draftkings"), None)
            if not bookmaker:
                continue
            details = {
                "game": f"{row['away_team']} @ {row['home_team']}", "sport": sport_name}
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    bet = details.copy()
                    bet.update({"market": market["key"], "pick": outcome.get(
                        "name"), "odds_american": outcome.get("price"), "line": outcome.get("point")})
                    normalized_odds.append(bet)

        if not normalized_odds:
            st.warning("No odds found from DraftKings.")
            return

        history_team = raw_odds[0]['home_team']
        if sport_key == "americanfootball_ncaaf":
            history = fetch_historical_ncaaf(history_team)
        elif sport_key == "americanfootball_nfl":
            history = fetch_historical_nfl(history_team)
        elif sport_key == "baseball_mlb":
            history = fetch_historical_mlb(history_team)
        else:
            history = []

        # --- 5. Generate Picks (The Super-Prompt now receives the Context) ---
        # NOTE: generate_ai_picks was updated to handle the context argument
        odds_df = pd.DataFrame(normalized_odds)

        # Pass the context payload to generate_ai_picks
        picks = generate_ai_picks(odds_df, history, sport=sport_name,
                                  context_payload=context_payload)
        st.session_state.generated_picks = picks

    # Clear the temporary status indicators after the whole process finishes
    status_placeholders['scrape'].empty()
    status_placeholders['api'].empty()
    status_placeholders['context'].empty()


# --- UI Controls (Buttons) ---
st.header("Generate New Picks")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏈 Generate NFL Picks", width="stretch"):
        st.session_state.generated_picks = None  # Clear previous results
        run_ai_picks("americanfootball_nfl", "NFL")
with col2:
    if st.button("🎓 Generate NCAAF Picks", width="stretch"):
        st.session_state.generated_picks = None
        run_ai_picks("americanfootball_ncaaf", "NCAAF")
with col3:
    if st.button("⚾ Generate MLB Picks", width="stretch"):
        st.session_state.generated_picks = None
        run_ai_picks("baseball_mlb", "MLB")


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
st.header("📜 AI Picks History")
ai_picks_history = list_ai_picks()
if ai_picks_history:
    df = pd.DataFrame(ai_picks_history)

    # Ensure confidence is a numeric type for correct sorting, defaulting errors to 0
    df['confidence_numeric'] = pd.to_numeric(
        df['confidence'], errors='coerce').fillna(0)

    # --- NEW: Sort by the numeric confidence score in descending order ---
    df.sort_values(by='confidence_numeric', ascending=False, inplace=True)

    # Convert confidence numbers to stars for display
    def score_to_stars(score):
        try:
            return "⭐" * max(1, min(5, int(score)))
        except (ValueError, TypeError):
            return "⭐"

    df['Confidence (Stars)'] = df['confidence_numeric'].apply(score_to_stars)

    # Define and reorder columns for display.
    # The 'result' column (Win/Loss/Pending) is now explicitly included.
    display_cols = ['date', 'sport', 'game', 'pick', 'market',
                    'line', 'odds_american', 'result', 'Confidence (Stars)', 'reasoning']

    # Rename the new confidence column for the final display
    df_display = df[display_cols].rename(
        columns={"Confidence (Stars)": "confidence"})

    st.dataframe(df_display, width="stretch", hide_index=True)
else:
    st.info("No AI picks have been saved yet.")
