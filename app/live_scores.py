# live_scores.py
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import streamlit as st

from app.rage_picks import fetch_scores

st.set_page_config(layout="wide", page_title="Live & Recent Scores")


def display_live_scores():

    # Add custom CSS to ensure full-width columns and proper spacing
    # Version: 2024-12-20-v2 (cache buster)
    st.markdown("""
        <style>
        /* Force full-width layout for columns - v2 */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 auto !important;
            min-width: 0 !important;
            padding: 0 8px !important;
        }

        /* Ensure equal column distribution */
        [data-testid="stHorizontalBlock"] {
            gap: 16px !important;
        }

        /* Prevent text wrapping in team names */
        .stMarkdown {
            width: 100% !important;
        }

        /* Force box to use full column width */
        .stMarkdown > div {
            width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Style Config ---
    box_style = """
        border: 1px solid black;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        color: black;
        background-color: #f0f0f0;
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        width: 100%;
    """
    status_style_live = "background-color: #d90429; color: white; padding: 2px 6px; border-radius: 4px; border: 1px solid black;"
    status_style_default = "color: var(--gray-60); font-size: 12px; font-weight: bold; white-space: nowrap;"
    team_style = "display: flex; justify-content: space-between; align-items: center; font-size: 14px; line-height: 1.3; margin: 4px 0; gap: 8px;"
    team_name_style = "flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0;"
    score_style = "font-weight: bold; font-size: 20px; min-width: 25px; text-align: right; flex-shrink: 0;"

    # --- Fetch scores (pulls 1 day of history) ---
    sports_data = {
        # "NFL": fetch_scores(sport="americanfootball_nfl", days_from=2),  # Season over
        # "NCAAF": fetch_scores(sport="americanfootball_ncaaf", days_from=2),  # Season over
        "MLB": fetch_scores(sport="baseball_mlb", days_from=2),
        "NCAAB": fetch_scores(sport="basketball_ncaab", days_from=2),
        "NBA": fetch_scores(sport="basketball_nba", days_from=2),
        "NHL": fetch_scores(sport="icehockey_nhl", days_from=2),
        "UFC": fetch_scores(sport="mma_mixed_martial_arts", days_from=2),
    }

    emojis = {"MLB": "⚾", "NCAAB": "🏀", "NBA": "🏀", "NHL": "🏒", "UFC": "🥊"}
    cols = st.columns(5)

    # Current UTC for cutoff logic
    now_utc = datetime.now(UTC)
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

            # --- Separate games by status ---
            completed_games = [
                g for g in filtered_games if g.get("completed", False)]
            live_games = [g for g in filtered_games if not g.get("completed", False)
                          and datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")) <= now_utc]
            upcoming_games = [
                g for g in filtered_games if g not in live_games and g not in completed_games]

            # Sort all categories by commence_time (earliest first)
            completed_games.sort(key=lambda g: datetime.fromisoformat(
                g.get("commence_time", "9999-12-31T23:59:59Z").replace("Z", "+00:00")
            ))
            live_games.sort(key=lambda g: datetime.fromisoformat(
                g.get("commence_time", "9999-12-31T23:59:59Z").replace("Z", "+00:00")
            ))
            upcoming_games.sort(key=lambda g: datetime.fromisoformat(
                g.get("commence_time", "9999-12-31T23:59:59Z").replace("Z", "+00:00")
            ))

            # Prioritize: LIVE first, then upcoming, then completed
            final_games = live_games + upcoming_games + completed_games

            # If no live games for UFC, show 5 upcoming (UFC events are less frequent)
            if sport == "UFC" and not live_games:
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
                            "%-I:%M%p PST").replace("AM", "am").replace("PM", "pm")
                        status_html = f'<div style="{status_style_default}">{date_str} - {time_str}</div>'

                st.markdown(
                    f"""
                    <div style="{box_style}">
                        <div style="text-align: center; margin-bottom: 10px;">{status_html}</div>
                        <div style="{team_style}">
                            <span style="{team_name_style}">{away}</span>
                            <span style="{score_style}">{away_score}</span>
                        </div>
                        <div style="{team_style}">
                            <span style="{team_name_style}">{home}</span>
                            <span style="{score_style}">{home_score}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
