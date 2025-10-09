# live_scores.py
import streamlit as st
from app.ai_picks import fetch_scores
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def display_live_scores():
    st.header("Live & Recent Scores")

    # --- Style Config ---
    box_style = """
        border: 1px solid black;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        background-color: var(--secondary-background-color);
    """
    status_style_live = "background-color: #d90429; color: white; padding: 2px 6px; border-radius: 4px; border: 1px solid black;"
    status_style_default = "color: var(--gray-60); font-size: 12px; font-weight: bold;"
    team_style = "display: flex; justify-content: space-between; align-items: center; font-size: 16px;"
    score_style = "font-weight: bold; font-size: 20px;"

    # --- Fetch scores (pulls 1 day of history) ---
    sports_data = {
        "NFL": fetch_scores(sport="americanfootball_nfl", days_from=1),
        "NCAAF": fetch_scores(sport="americanfootball_ncaaf", days_from=1),
        "MLB": fetch_scores(sport="baseball_mlb", days_from=1),
        "NBA": fetch_scores(sport="basketball_nba", days_from=1),
    }

    emojis = {"NFL": "🏈", "NCAAF": "🎓", "MLB": "⚾️", "NBA": "🏀"}
    cols = st.columns(4)

    # Current UTC for cutoff logic
    now_utc = datetime.now(timezone.utc)
    cutoff_utc = now_utc - timedelta(hours=8)

    for idx, (sport, games) in enumerate(sports_data.items()):
        with cols[idx]:
            st.subheader(f"{emojis[sport]} {sport}")

            if not games:
                st.info(f"No recent {sport} scores available.")
                continue

            # --- Filter: remove games older than 8 hours ---
            filtered_games = []
            for g in games:
                commence_str = g.get("commence_time")
                if not commence_str:
                    continue
                try:
                    commence_dt = datetime.fromisoformat(
                        commence_str.replace("Z", "+00:00")
                    )
                except Exception:
                    continue
                # Keep only games that started within last 8h OR upcoming
                if commence_dt >= cutoff_utc:
                    filtered_games.append(g)

            # --- Prioritize LIVE games ---
            live_games = [g for g in filtered_games if not g.get("completed", False)
                          and datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")) <= now_utc]
            upcoming_games = [g for g in filtered_games if g not in live_games]
            final_games = live_games + upcoming_games

            # If no live games for NCAAF, show 5 upcoming
            if sport == "NCAAF" and not live_games:
                final_games = upcoming_games[:5]

            # --- Display games ---
            for g in final_games[:10]:
                home = g.get("home_team", "N/A")
                away = g.get("away_team", "N/A")
                scores = g.get("scores") or []
                home_score = next((s.get("score")
                                  for s in scores if s.get("name") == home), "-")
                away_score = next((s.get("score")
                                  for s in scores if s.get("name") == away), "-")

                is_complete = g.get("completed", False)
                commence_str = g.get("commence_time")
                status_html = ""

                if is_complete:
                    status_html = f'<div style="{status_style_default}">FINAL</div>'
                elif commence_str:
                    utc_time = datetime.fromisoformat(
                        commence_str.replace("Z", "+00:00"))
                    if utc_time <= now_utc:
                        status_html = f'<div style="{status_style_default}"><span style="{status_style_live}">LIVE</span></div>'
                    else:
                        pst_tz = ZoneInfo("America/Los_Angeles")
                        pst_time = utc_time.astimezone(pst_tz)
                        date_str = pst_time.strftime("%m/%d")
                        time_str = pst_time.strftime(
                            "%-I:%M %p PST").replace(" AM", "am").replace(" PM", "pm")
                        status_html = f'<div style="{status_style_default}">{date_str} - {time_str}</div>'

                st.markdown(
                    f"""
                    <div style="{box_style}">
                        <div style="text-align: center; margin-bottom: 8px;">{status_html}</div>
                        <div style="{team_style}">
                            <span>{away}</span>
                            <span style="{score_style}">{away_score}</span>
                        </div>
                        <div style="{team_style} margin-top: 4px;">
                            <span>{home}</span>
                            <span style="{score_style}">{home_score}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
