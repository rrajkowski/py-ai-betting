# streamlit_app.py
import pandas as pd
import streamlit as st

from app.db import init_db, insert_bet, list_bets, init_ai_picks
from app.utils.db import init_prompt_context_db  # NEW: Import for new table setup
from app.ai_picks import fetch_odds


# --- DBs init ---
init_db()
init_ai_picks()
init_prompt_context_db()  # NEW: Initialize the prompt_context table

st.title("⚡ AI Sports Betting Dashboard")

# -----------------------------
# AI Daily Picks Section
# -----------------------------
st.set_page_config(
    page_title="AI Betting App",
    page_icon="🏆",
    layout="wide"
)

st.page_link("pages/ai_picks_page.py", label="🤖 Go to AI Daily Picks")


# -----------------------------
# Make a Bet Section
# -----------------------------
st.header("🏈 Make a Bet")

# --- Sport and Game Selection ---
sports_map = {
    "NFL (American Football)": "americanfootball_nfl",
    "College Football (NCAAF)": "americanfootball_ncaaf",
    # "Major League Baseball (MLB)": "baseball_mlb",  # Season over
    "College Basketball (NCAAB)": "basketball_ncaab",
    "National Basketball Association (NBA)": "basketball_nba",
}
sport_label = st.selectbox("Select Sport", list(sports_map.keys()))
sport_key = sports_map[sport_label]

games_data = fetch_odds(sport_key)
if not games_data:
    st.info("⚠️ No games available for this sport right now.")
else:
    game = st.selectbox(
        "Select Game",
        games_data,
        format_func=lambda g: f"{g['away_team']} @ {g['home_team']} ({g['commence_time']})",
    )
    home_team = game['home_team']
    away_team = game['away_team']

    # --- Bet Details ---
    col1, col2 = st.columns(2)
    with col1:
        market_key = st.selectbox("Market", ["h2h", "spreads", "totals"])
    with col2:
        stake = st.number_input(
            "Stake (USD)", min_value=1.0, step=1.0, value=100.0)

    # --- Dynamic Outcome Selection ---
    # Find the odds from the first available bookmaker (e.g., DraftKings)
    odds_data = None
    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == market_key:
                odds_data = market
                break

    if odds_data and odds_data.get("outcomes"):
        # Dynamically format the outcome choices based on the selected market
        if market_key in ["spreads", "totals"]:
            outcomes = {
                f"{o['name']} {o['point']} @ {o['price']}": o for o in odds_data["outcomes"]}
        else:  # h2h
            outcomes = {
                f"{o['name']} @ {o['price']}": o for o in odds_data["outcomes"]}

        pick_label = st.selectbox("Select Outcome", list(outcomes.keys()))

        if st.button("💰 Place Bet"):
            picked_outcome = outcomes[pick_label]

            # Determine team and opponent based on market type
            if market_key in ["h2h", "spreads"]:
                team_picked = picked_outcome['name']
                opponent = home_team if team_picked == away_team else away_team
                success_message = f"Bet saved: {team_picked} ({market_key}) @ {picked_outcome['price']}"
            else:  # totals
                team_picked = picked_outcome['name']  # "Over" or "Under"
                opponent = f"{away_team} @ {home_team}"
                success_message = f"Bet saved: {team_picked} {picked_outcome['point']} @ {picked_outcome['price']}"

            # Insert the bet into the database
            insert_bet(
                team=team_picked,
                opponent=opponent,
                market=market_key,
                stake=stake,
                odds_american=picked_outcome["price"],
                line=picked_outcome.get("point")
            )
            st.success(f"✅ {success_message}")
    else:
        st.warning(f"Odds for '{market_key}' are not available for this game.")


# -----------------------------
# Bet History + ROI Section
# -----------------------------
st.header("Bet History & ROI")

bets_data = list_bets()
df = pd.DataFrame(bets_data)

if df.empty:
    st.info("No bets yet. Place a bet above.")
else:
    df["date"] = pd.to_datetime(df["date"])

    # Derive profit_units if missing
    if "profit" in df.columns:
        df["profit_units"] = df["profit"] / 50.0  # 1 unit = $50

    # Show explicit columns including new 'line' + profit_units
    cols_to_show = [
        "id", "team", "opponent", "market",
        "stake", "odds_american", "line", "probability",
        "profit", "profit_units", "date"
    ]
    available_cols = [c for c in cols_to_show if c in df.columns]

    st.dataframe(df[available_cols].head(10))

    if "profit" in df.columns and "stake" in df.columns:
        total_profit_dollars = df["profit"].sum(skipna=True)
        total_profit_units = df["profit_units"].sum(skipna=True)
        total_stake = df["stake"].sum(skipna=True)

        roi = total_profit_dollars / total_stake if total_stake > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("ROI", f"{roi:.2%}")
        col2.metric("Total Profit ($)", f"{total_profit_dollars:.2f}")
        col3.metric("Total Profit (Units)", f"{total_profit_units:.2f}u")

        # Add cumulative profit trend (in dollars)
        st.line_chart(df.groupby("date")["profit"].sum().cumsum())


# -----------------------------
# Live & Recent Scores
# -----------------------------
# display_live_scores()
