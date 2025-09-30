# live_scores.py
import streamlit as st
from app.ai_picks import fetch_scores


def display_live_scores():
    st.header("Live & Recent Scores")

    nfl_scores = fetch_scores("americanfootball_nfl")
    ncaaf_scores = fetch_scores("americanfootball_ncaaf")
    mlb_scores = fetch_scores("baseball_mlb")

    sports_data = {
        "NFL": [s for s in nfl_scores[:10]],
        "NCAAF": [s for s in ncaaf_scores[:10]],
        "MLB": [s for s in mlb_scores[:10]]
    }

    emojis = {
        "NFL": "🏈",
        "NCAAF": "🏈",
        "MLB": "⚾️"
    }

    cols = st.columns(3)

    for idx, (sport, games) in enumerate(sports_data.items()):
        with cols[idx]:
            st.subheader(f"{sport} {emojis[sport]}")

            if not games:
                st.info(f"No recent {sport} scores available.")
            else:
                for g in games:
                    home = g.get("home_team", "")
                    away = g.get("away_team", "")
                    scores_list = g.get("scores") or []
                    home_score = next(
                        (s.get("score") for s in scores_list if s.get("name") == home), None)
                    away_score = next(
                        (s.get("score") for s in scores_list if s.get("name") == away), None)

                    away_winner = "🏆" if home_score and away_score and int(
                        away_score) > int(home_score) else ""
                    home_winner = "🏆" if home_score and away_score and int(
                        home_score) > int(away_score) else ""

                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid #444;
                            border-radius: 8px;
                            padding: 12px;
                            margin-bottom: 12px;
                            text-align: center;
                            background-color: #1e1e1e;
                            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
                            min-height: 100px;
                            max-height: 100px;
                            overflow: hidden;
                        ">
                            <div style="font-size: 18px; font-weight: bold; margin-bottom: 4px;">{away} <span style="font-size: 22px; color: #66b3ff;">{away_score or '-'}</span> {away_winner}</div>
                            <div style="font-size: 18px; font-weight: bold;">{home} <span style="font-size: 22px; color: #66b3ff;">{home_score or '-'}</span> {home_winner}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
