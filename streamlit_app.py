import streamlit as st
import pandas as pd
import requests
import os

# --- Resolve backend API URL ---
FASTAPI_URL = os.getenv("FASTAPI_URL", "https://py-ai-betting.vercel.app/api")

# Default fallbacks:
# 1. If running on Vercel, FASTAPI_URL will be set in the dashboard
# 2. If running on Streamlit Cloud (no backend), fallback to public Vercel URL
# 3. If running locally, fallback to localhost
if not FASTAPI_URL:
    if "VERCEL_URL" in os.environ:
        # Running inside Vercel
        FASTAPI_URL = f"https://{os.environ['VERCEL_URL']}"
    elif "STREAMLIT_SERVER_PORT" in os.environ:
        # Likely running inside Streamlit Cloud
        FASTAPI_URL = "https://py-ai-betting.vercel.app"
    else:
        # Local development
        FASTAPI_URL = "http://127.0.0.1:8000"

st.sidebar.info(f"Using backend: {FASTAPI_URL}")
st.title("⚡ AI Sports Betting Dashboard")

# -----------------------------
# Odds + Suggestion Section
# -----------------------------
st.header("Make a Bet")

# Choose sport
sports_map = {
    "College Football (NCAAF)": "americanfootball_ncaaf",
    "Major League Baseball (MLB)": "baseball_mlb",
    "NFL (American Football)": "americanfootball_nfl",
}
sport_label = st.selectbox("Select Sport", list(sports_map.keys()))
sport = sports_map[sport_label]

# Fetch games from FastAPI
games_resp = requests.get(f"{FASTAPI_URL}/games/{sport}")
games_data = []
if games_resp.status_code == 200:
    games_data = games_resp.json().get("games", [])
else:
    st.error(f"Error fetching games: {games_resp.text}")

# Pick game
if games_data:
    game = st.selectbox(
        "Select Game",
        games_data,
        format_func=lambda g: f"{g['home_team']} vs {g['away_team']} ({g['commence_time']})"
    )

    if game:
        # Show market choices from schema: h2h, spreads, totals
        available_markets = list(game.get("odds", {}).keys())
        if not available_markets:
            st.warning("No markets available for this game.")
        else:
            market = st.selectbox("Market", available_markets)

            # Show available sides based on chosen market
            sides = list(game["odds"][market].keys())
            side = st.selectbox("Side", sides)

            # Odds value for the chosen side
            odds_value = None
            if market in game["odds"] and side in game["odds"][market]:
                odds_value = game["odds"][market][side]

            st.write(f"**Odds for {side}: {game['odds'][market][side]}**")

            if st.button("Suggest Bet"):
                payload = {
                    "game_id": game["game_id"],
                    "sport": game["sport"],
                    "market": market,
                    "side": side,
                    "match": f"{game['home_team']} vs {game['away_team']}",
                    "bet_type": market,
                    "odds": odds_value,
                    "stats": {}  # optional placeholder
                }
                resp = requests.post(
                    f"{FASTAPI_URL}/bets/suggest", json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    st.success(
                        f"Bet saved: Probability={result['probability']:.2f}, "
                        f"EV={result['expected_value']:.3f}"
                    )
                else:
                    st.error(f"Error: {resp.text}")
else:
    st.info("No games available right now for this sport.")

# -----------------------------
# Bets History + ROI Section
# -----------------------------
st.header("Bet History & ROI")

bets_resp = requests.get(f"{FASTAPI_URL}/bets")
if bets_resp.status_code == 200:
    bets_data = bets_resp.json().get("bets", [])
    df = pd.DataFrame(bets_data)
else:
    st.error(f"Error fetching bets: {bets_resp.text}")
    df = pd.DataFrame()

if df.empty:
    st.info("No bets yet. Suggest a bet above to get started.")
else:
    df["date"] = pd.to_datetime(df["date"])
    st.dataframe(df.tail(10))  # show last 10 entries

    total_profit = df["profit"].sum(skipna=True)
    total_stake = df["stake"].sum(skipna=True)
    roi = total_profit / total_stake if total_stake > 0 else 0

    col1, col2 = st.columns(2)
    col1.metric("ROI", f"{roi:.2%}")
    col2.metric("Total Profit", f"{total_profit:.2f} units")

    st.line_chart(df.groupby("date")["profit"].sum().cumsum())
