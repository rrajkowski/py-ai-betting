import streamlit as st
import pandas as pd
from app.db import init_db, insert_bet, list_bets

# Initialize DB on startup
init_db()

st.title("⚡ AI Sports Betting Dashboard")

# -----------------------------
# Odds + Suggestion Section
# -----------------------------
st.header("Make a Bet")

# For now, keep this simple since no FastAPI odds feed:
sports_map = {
    "College Football (NCAAF)": "americanfootball_ncaaf",
    "Major League Baseball (MLB)": "baseball_mlb",
    "NFL (American Football)": "americanfootball_nfl",
}
sport_label = st.selectbox("Select Sport", list(sports_map.keys()))
sport = sports_map[sport_label]

team = st.text_input("Team")
opponent = st.text_input("Opponent")
market = st.selectbox("Market", ["h2h", "spreads", "totals"])

if st.button("Save Bet"):
    if team and opponent and market:
        insert_bet(team, opponent, market)
        st.success(f"Saved bet: {team} vs {opponent} ({market})")
    else:
        st.warning("Fill in all fields before saving a bet.")

# -----------------------------
# Bets History + ROI Section
# -----------------------------
st.header("Bet History & ROI")

bets_data = list_bets()
df = pd.DataFrame(bets_data)

if df.empty:
    st.info("No bets yet. Suggest a bet above to get started.")
else:
    df["date"] = pd.to_datetime(df["date"])
    st.dataframe(df.head(10))  # show 10 most recent bets

    # Optional ROI / Profit if schema has stake/profit
    if "profit" in df.columns and "stake" in df.columns:
        total_profit = df["profit"].sum(skipna=True)
        total_stake = df["stake"].sum(skipna=True)
        roi = total_profit / total_stake if total_stake > 0 else 0

        col1, col2 = st.columns(2)
        col1.metric("ROI", f"{roi:.2%}")
        col2.metric("Total Profit", f"{total_profit:.2f} units")

        st.line_chart(df.groupby("date")["profit"].sum().cumsum())
