import streamlit as st
import requests
import json
import os
import sqlite3
from datetime import datetime, timezone
from openai import OpenAI
import google.generativeai as genai
from .db import get_db, init_ai_picks, insert_ai_picks
from .const import RAPIDAPI_KEY, HEADERS
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# -------------------------
# DB Migration for historical_games
# -------------------------


def migrate_historical_games():
    """Ensures the historical_games table exists with full schema."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historical_games (
            id TEXT PRIMARY KEY,
            sport TEXT,
            game TEXT,
            score TEXT,
            winner TEXT,
            date TEXT,
            home_team TEXT,
            away_team TEXT
        )
    """)
    cur.execute("PRAGMA table_info(historical_games)")
    cols = {row['name'] for row in cur.fetchall()}
    if "home_team" not in cols:
        cur.execute("ALTER TABLE historical_games ADD COLUMN home_team TEXT")
    if "away_team" not in cols:
        cur.execute("ALTER TABLE historical_games ADD COLUMN away_team TEXT")
    conn.commit()
    conn.close()


init_ai_picks()
migrate_historical_games()

# -------------------------
# Odds & Scores APIs
# -------------------------


def fetch_odds(sport="americanfootball_ncaaf"):
    """
    Fetches odds from the API and filters out any games that have already started.
    """
    url = f"https://odds.p.rapidapi.com/v4/sports/{sport}/odds"
    querystring = {
        "regions": "us", "oddsFormat": "american",
        "markets": "h2h,spreads,totals", "dateFormat": "iso"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "odds.p.rapidapi.com"
    }
    r = requests.get(url, headers=headers, params=querystring)
    r.raise_for_status()
    all_games = r.json()

    now_utc = datetime.now(timezone.utc)
    future_games = []
    for game in all_games:
        commence_time_str = game.get('commence_time')
        if not commence_time_str:
            continue
        try:
            commence_time = datetime.fromisoformat(
                commence_time_str.replace("Z", "+00:00"))
            if commence_time > now_utc:
                future_games.append(game)
        except ValueError:
            continue
    return future_games


def fetch_scores(sport="americanfootball_ncaaf", days_from=1):
    url = f"https://odds.p.rapidapi.com/v4/sports/{sport}/scores"
    params = {"daysFrom": days_from}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()
# -------------------------
# Historical Data Caching
# -------------------------


def _fetch_and_cache_historical_scores(sport_key, sport_name, team, limit=6, days_from=20):
    conn = get_db()
    cur = conn.cursor()
    history = []
    query = "SELECT * FROM historical_games WHERE sport = ? AND (home_team = ? OR away_team = ?) ORDER BY date DESC LIMIT ?"
    cur.execute(query, (sport_name, team, team, limit))
    cached_games = [dict(row) for row in cur.fetchall()]

    if len(cached_games) >= limit:
        conn.close()
        return cached_games

    try:
        scores_data = fetch_scores(sport=sport_key, days_from=days_from)
    except Exception:
        conn.close()
        return []

    for game in scores_data:
        if not game.get('completed', False):
            continue
        home_team = game.get('home_team')
        away_team = game.get('away_team')
        home_score = next((s['score'] for s in game.get(
            'scores', []) if s['name'] == home_team), '0')
        away_score = next((s['score'] for s in game.get(
            'scores', []) if s['name'] == away_team), '0')
        if not home_score or not away_score:
            continue

        record = {
            "id": game.get('id'),
            "sport": sport_name,
            "game": f"{away_team} @ {home_team}",
            "score": f"{home_score}-{away_score}",
            "winner": home_team if int(home_score) > int(away_score) else away_team,
            "date": game.get('commence_time'),
            "home_team": home_team,
            "away_team": away_team,
        }
        cur.execute("""
            INSERT OR IGNORE INTO historical_games (id, sport, game, score, winner, date, home_team, away_team)
            VALUES (:id, :sport, :game, :score, :winner, :date, :home_team, :away_team)
        """, record)
        if team in (home_team, away_team):
            history.append(record)

    conn.commit()
    conn.close()
    return sorted(history, key=lambda x: x['date'], reverse=True)[:limit]


def fetch_historical_ncaaf(team_name, limit=30): return _fetch_and_cache_historical_scores(
    "americanfootball_ncaaf", "NCAAF", team_name, limit)


def fetch_historical_nfl(team_name, limit=16): return _fetch_and_cache_historical_scores(
    "americanfootball_nfl", "NFL", team_name, limit)


def fetch_historical_mlb(team_name, limit=10): return _fetch_and_cache_historical_scores(
    "baseball_mlb", "MLB", team_name, limit)


def fetch_historical_nba(team_name, limit=10): return _fetch_and_cache_historical_scores(
    "basketball_nba", "NBA", team_name, limit)


def fetch_historical_other(team_name, limit=10): return []

# -------------------------
# AI Model Helpers
# -------------------------


def _call_openai_model(model_name, prompt):
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set.")
    client = OpenAI(api_key=OPENAI_API_KEY)
    req = dict(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a betting assistant returning valid JSON."},
            {"role": "user", "content": f"Return picks JSON only:\n\n{prompt}"}
        ],
        response_format={"type": "json_object"},
        timeout=90.0,
    )
    if not model_name.startswith("gpt-5"):
        req["temperature"] = 0.6
    resp = client.chat.completions.create(**req)
    raw = resp.choices[0].message.content
    try:
        return json.loads(raw).get("picks", [])
    except Exception:
        return []


def _call_gemini_model(model_name, prompt):
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set.")
    gen_config = genai.types.GenerationConfig(
        response_mime_type="application/json")
    model = genai.GenerativeModel(model_name, generation_config=gen_config)
    resp = model.generate_content(prompt)
    return json.loads(resp.text).get("picks", [])

# -------------------------
# Generate AI Picks
# -------------------------


def generate_ai_picks(odds_df, history_data, sport="unknown", context_payload=None, kalshi_context=None):
    """
    Generate betting picks with robust data enrichment to ensure commence_time is saved.
    """
    context = {
        "odds_count": len(odds_df),
        "sport": sport.upper(),
        "sample_odds": odds_df.head(15).to_dict(orient="records"),
        "history": history_data,
    }
    if context_payload:
        context["extra_context"] = context_payload
    if kalshi_context:
        context["kalshi"] = kalshi_context

    prompt = f"""
    You are a hyper-efficient sports betting analyst. Your goal is to quickly identify the best value bets.
    Instructions:
    1. Analyze the provided context, including odds, historical performance, and Kalshi sentiment data (popularity_score, volume_24h, open_interest).
    2. Focus only on strong, data-supported bets.
    3. Critically, only select games where the `commence_time` is in the future. Do not pick games that have already started.
    4. Each object in the "picks" list MUST contain these exact keys: "game", "sport", "pick", "market", "line", "odds_american", "confidence", "reasoning".
    5. Only include picks with **confidence ratings of 3, 4, or 5 stars**. (Do NOT return any 1-star or 2-star picks.)
    6. The "odds_american" field must be numeric (e.g., -110, 150).
    7. All picks must be for DIFFERENT GAMES.
    8. Exclude odds outside the range (+150 to -150).
    9. The reasoning must clearly connect odds + sentiment to confidence.
    10. Return a maximum of 3 picks. If no picks meet the 3-star threshold, return an empty "picks" list.
    Context: {json.dumps(context, indent=2)}
    """

    models = [
        {'provider': 'google', 'name': 'gemini-2.5-pro'},
        {'provider': 'openai', 'name': 'gpt-5-mini'},
        {'provider': 'openai', 'name': 'gpt-5-nano'},
    ]

    parsed = []
    for m in models:
        try:
            if m['provider'] == 'google':
                parsed = _call_gemini_model(m['name'], prompt)
            else:
                parsed = _call_openai_model(m['name'], prompt)

            if parsed:
                st.success(
                    f"Generated {len(parsed)} picks using {m['provider']}:{m['name']}")
                break
        except Exception as e:
            st.warning(f"{m['name']} failed: {e}")
            continue

    if not parsed:
        st.error("All models failed to generate picks.")
        return []

    unique_picks, seen = [], set()
    for pick in parsed:
        pick.setdefault("sport", sport)
        try:
            if int(pick.get("confidence", 0)) < 3:
                continue
        except (ValueError, TypeError):
            continue

        # --- Use robust matching to find and add commence_time ---
        try:
            ai_game_string = pick.get('game', '').lower()
            if not ai_game_string:
                continue

            # Iterate through the original odds data to find a reliable match
            for _, row in odds_df.iterrows():
                away_team_full = row.get('away_team', '').lower()
                home_team_full = row.get('home_team', '').lower()

                # ** Ensure team names are not empty before splitting
                if away_team_full and home_team_full:
                    # Isolate mascot names for more flexible matching
                    away_mascot = away_team_full.split()[-1]
                    home_mascot = home_team_full.split()[-1]

                    # Check if both mascots are present in the AI's game string
                    if away_mascot and home_mascot and \
                       away_mascot in ai_game_string and home_mascot in ai_game_string:

                        # If odds are missing, populate them from the matched row
                        if 'odds_american' not in pick or pick.get('odds_american') is None:
                            pick['odds_american'] = row['odds_american']

                        # ALWAYS populate commence_time from the definitive source
                        pick['commence_time'] = row['commence_time']
                        break  # Stop searching once a match is found
        except Exception as e:
            st.warning(f"Could not enrich pick for '{pick.get('game')}': {e}")
            pass

        gm_key = (pick.get('game', '').strip(), pick.get('market', '').strip())
        if gm_key in seen:
            continue
        seen.add(gm_key)
        unique_picks.append(pick)

    if unique_picks:
        insert_ai_picks(unique_picks)
        st.toast(f"Saved {len(unique_picks)} new picks.")
    else:
        st.toast("No new picks to save.")

    return parsed
# -------------------------
# Auto-grading and Match Time Sync
# -------------------------


def update_ai_pick_results():
    """
    Auto-updates AI picks from 'Pending' to Win/Loss/Push
    based on fetched live/final scores.
    """
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, game, pick, sport, commence_time FROM ai_picks WHERE LOWER(result)='pending'")
    pending = cur.fetchall()
    if not pending:
        print("No pending picks to update.")
        conn.close()
        return

    print(f"🔍 Checking {len(pending)} pending picks...")
    updated = 0

    for row in pending:
        sport = row["sport"].lower().replace(" ", "_")
        commence = row["commence_time"]
        if not commence:
            continue
        commence_dt = datetime.fromisoformat(commence.replace("Z", "+00:00"))
        if datetime.now(timezone.utc) < commence_dt:
            continue

        try:
            scores = fetch_scores(sport=sport, days_from=2)
        except Exception:
            continue

        for g in scores:
            if not g.get("completed"):
                continue
            if g.get("home_team") in row["game"] and g.get("away_team") in row["game"]:
                home, away = g["home_team"], g["away_team"]
                hs = next((s["score"]
                          for s in g["scores"] if s["name"] == home), None)
                as_ = next((s["score"]
                           for s in g["scores"] if s["name"] == away), None)
                if hs is None or as_ is None:
                    continue
                result = "Push"
                if int(hs) == int(as_):
                    result = "Push"
                elif (row["pick"] == home and int(hs) > int(as_)) or \
                     (row["pick"] == away and int(as_) > int(hs)):
                    result = "Win"
                else:
                    result = "Loss"

                cur.execute("UPDATE ai_picks SET result=? WHERE id=?",
                            (result, row["id"]))
                updated += 1
                break

    conn.commit()
    conn.close()
    print(f"✅ Updated {updated} picks.")
