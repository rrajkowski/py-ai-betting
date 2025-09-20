import streamlit as st
import sqlite3
import pandas as pd

st.title("AI Sports Betting Dashboard")

conn = sqlite3.connect("bets.db")
try:
    df = pd.read_sql("SELECT * FROM bets", conn)
except Exception:
    st.warning("No bets table found yet. Run FastAPI once to initialize the DB.")
    df = pd.DataFrame()
conn.close()

if df.empty:
    st.info("No bets yet. Use the FastAPI endpoints to add some.")
else:
    df["date"] = pd.to_datetime(df["date"])
    st.dataframe(df)

    total_profit = df["profit"].sum(skipna=True)
    roi = total_profit / df["stake"].sum()
    st.metric("ROI", f"{roi:.2%}")
    st.metric("Total Profit", f"{total_profit:.2f} units")

    st.line_chart(df.groupby("date")["profit"].sum().cumsum())
