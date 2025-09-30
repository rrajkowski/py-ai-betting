import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from app.db import get_most_recent_pick_timestamp, list_ai_picks, init_ai_picks
from app.ai_picks import (
    fetch_odds,
    fetch_historical_nfl,
    fetch_historical_mlb,
    fetch_historical_ncaaf,
    generate_ai_picks
)

# Run at import to guarantee schema is correct
init_ai_picks()

# --- Page Configuration & Title ---
st.set_page_config(page_title="🤖 AI Daily Picks", layout="wide")
st.title("🤖 AI Daily Picks")
st.markdown(
    "Click a button to generate AI-recommended bets for that sport. Picks are generated once per day.")

# --- Initialize Session State ---
# This is crucial for making new picks appear instantly.
if 'generated_picks' not in st.session_state:
    st.session_state.generated_picks = None

# -----------------------------
# Main AI Pick Generation Logic
# -----------------------------


def run_ai_picks(sport_key, sport_name):
    # ... (This function is unchanged, as the error is in the display logic) ...
    last_pick_time = get_most_recent_pick_timestamp(sport_name)
    if last_pick_time and (datetime.now() - last_pick_time < timedelta(hours=24)):
        st.info(
            f"Picks for {sport_name} were generated today. Last generated: {last_pick_time.strftime('%Y-%m-%d %I:%M %p')}")
        return

    with st.spinner(f"AI is analyzing {sport_name} games... This can take up to a minute."):
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

        odds_df = pd.DataFrame(normalized_odds)
        picks = generate_ai_picks(odds_df, history, sport=sport_name)
        st.session_state.generated_picks = picks


# --- UI Controls (Buttons) ---
st.header("Generate New AI Picks")
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
        cols = st.columns(len(picks) if len(picks) <= 3 else 3)
        for i, pick in enumerate(picks):
            with cols[i % 3]:
                with st.container(border=True):
                    # --- NEW: Check if 'pick' is a dictionary before processing ---
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

    # Define and reorder columns for display
    display_cols = ['date', 'sport', 'game', 'pick', 'market',
                    'line', 'odds_american', 'Confidence (Stars)', 'reasoning']

    # Rename the new confidence column for the final display
    df_display = df[display_cols].rename(
        columns={"Confidence (Stars)": "confidence"})

    st.dataframe(df_display, width="stretch", hide_index=True)
else:
    st.info("No AI picks have been saved yet.")
