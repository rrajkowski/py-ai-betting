import streamlit as st
import requests
import json
import os
from openai import OpenAI
import google.generativeai as genai
from .db import get_db, init_ai_picks
from .const import RAPIDAPI_KEY, HEADERS

# --- Load API Keys from .env ---
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# --- NEW: Schema migration for historical_games table ---


def migrate_historical_games():
    """
    Ensures the historical_games table exists with the correct, final schema.
    This is the single source of truth for this table's structure.
    """
    conn = get_db()
    cur = conn.cursor()

    # Create the table with the complete schema if it doesn't exist
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

    # For backward compatibility, check for and add columns if missing from an old DB
    cur.execute("PRAGMA table_info(historical_games)")
    # Use a set for faster lookups
    cols = {row['name'] for row in cur.fetchall()}

    if "home_team" not in cols:
        cur.execute("ALTER TABLE historical_games ADD COLUMN home_team TEXT")
    if "away_team" not in cols:
        cur.execute("ALTER TABLE historical_games ADD COLUMN away_team TEXT")

    conn.commit()
    conn.close()


# --- Run Migrations on Import ---
init_ai_picks()
migrate_historical_games()


# -------------------------
# Odds & Scores APIs
# -------------------------
def fetch_odds(sport="americanfootball_ncaaf"):
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
    return r.json()


def fetch_scores(sport="americanfootball_ncaaf", days_from=1):
    url = f"https://odds.p.rapidapi.com/v4/sports/{sport}/scores"
    params = {"daysFrom": days_from}
    r = requests.get(url, headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


# --- Historical Data Caching & Fetching (CORRECTED) ---
def _fetch_and_cache_historical_scores(sport_key, sport_name, team, limit=5, days_from=14):
    conn = get_db()
    cur = conn.cursor()
    history = []

    # 1. Check cache using CORRECT schema (home_team, away_team)
    query = "SELECT * FROM historical_games WHERE sport = ? AND (home_team = ? OR away_team = ?) ORDER BY date DESC LIMIT ?"
    cur.execute(query, (sport_name, team, team, limit))
    cached_games = [dict(row) for row in cur.fetchall()]

    if len(cached_games) >= limit:
        st.write(
            f"Found {len(cached_games)} cached historical games for {team}.")
        conn.close()
        return cached_games

    # 2. Fallback to live API
    st.write(
        f"No sufficient cache for {team}. Fetching live scores from API...")
    try:
        scores_data = fetch_scores(sport=sport_key, days_from=days_from)
    except Exception:
        conn.close()
        return []

    # 3. Parse and update cache using CORRECT schema
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
            "id": game.get('id'), "sport": sport_name,
            "game": f"{away_team} @ {home_team}", "score": f"{home_score}-{away_score}",
            "winner": home_team if int(home_score) > int(away_score) else away_team,
            "date": game.get('commence_time'), "home_team": home_team, "away_team": away_team
        }
        cur.execute("""
            INSERT OR IGNORE INTO historical_games (id, sport, game, score, winner, date, home_team, away_team)
            VALUES (:id, :sport, :game, :score, :winner, :date, :home_team, :away_team)
        """, record)
        if team == home_team or team == away_team:
            history.append(record)

    conn.commit()
    conn.close()
    return sorted(history, key=lambda x: x['date'], reverse=True)[:limit]

# --- Wrapper Functions (Unchanged) ---


def fetch_historical_ncaaf(team_name="Alabama Crimson Tide", limit=5):
    return _fetch_and_cache_historical_scores("americanfootball_ncaaf", "NCAAF", team_name, limit)


def fetch_historical_nfl(team_name="Kansas City Chiefs", limit=5):
    return _fetch_and_cache_historical_scores("americanfootball_nfl", "NFL", team_name, limit)


def fetch_historical_mlb(team_name="Los Angeles Dodgers", limit=5):
    return _fetch_and_cache_historical_scores("baseball_mlb", "MLB", team_name, limit)

# -------------------------
# AI Model Helper Functions
# -------------------------


def _call_openai_model(model_name, prompt):
    """Sends a prompt to an OpenAI model and returns the parsed 'picks'."""
    client = OpenAI()
    st.write(f"Generating picks with OpenAI model: {model_name}...")
    resp = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        timeout=90.0
    )
    raw_output = resp.choices[0].message.content
    return json.loads(raw_output).get("picks", [])


def _call_gemini_model(model_name, prompt):
    """Sends a prompt to a Gemini model and returns the parsed 'picks'."""
    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not found. Please set it in your .env file.")

    st.write(f"Generating picks with Google model: {model_name}...")
    # Enforce JSON output for Gemini
    generation_config = genai.types.GenerationConfig(
        response_mime_type="application/json")
    model = genai.GenerativeModel(
        model_name, generation_config=generation_config)

    resp = model.generate_content(prompt)
    return json.loads(resp.text).get("picks", [])

# In app/ai_picks.py


def generate_ai_picks(odds_df, history_data, sport="unknown"):
    """
    Generate betting picks using a multi-tier model fallback system,
    with validation to handle malformed AI responses.
    """
    # --- 1. Define the context for the AI ---
    context = {
        "odds_count": len(odds_df),
        "sport": sport.upper(),
        "sample_odds": odds_df.head(15).to_dict(orient="records"),
        "history": history_data,
    }

    # --- 2. Define the high-quality prompt ---
    prompt = f"""
    You are a hyper-efficient sports betting analyst. Your goal is to quickly identify the best value bet for each of the three main markets (h2h, spreads, totals).

    Instructions:
    - The 'confidence' value MUST be an integer from 2 (medium) to 5 (high).
    - Do not return any 1-star (low confidence) picks.
    - It is better to return only one or two excellent picks than three mediocre ones.
    - If no bets meet the 2-star confidence threshold, return an empty "picks" list.
    - All picks must be for DIFFERENT GAMES.
    - Return your findings as a valid JSON object with the key "picks".

    Context: {json.dumps(context, indent=2)}
    """

    # --- REMOVED: The unused 'client = OpenAI()' line was here. ---

    models_to_try = [
        {'provider': 'google', 'name': 'gemini-2.5-pro'},  # Primary: Gemini
        {'provider': 'openai', 'name': 'gpt-5-mini'},     # Fallback 1: gpt-5-mini
        {'provider': 'openai', 'name': 'gpt-5'},          # Fallback 2: gpt-5
    ]

    parsed = []
    for model in models_to_try:
        try:
            if model['provider'] == 'google':
                parsed = _call_gemini_model(model['name'], prompt)
            elif model['provider'] == 'openai':
                parsed = _call_openai_model(model['name'], prompt)

            if parsed:
                st.success(
                    f"Successfully generated {len(parsed)} picks using {model['provider']}'s {model['name']}!")
                break
            else:
                st.warning(
                    f"Model {model['name']} returned no picks. Trying next model...")
        except Exception as e:
            st.warning(
                f"Model {model['name']} failed: {e}. Trying next model...")
            continue

    if not parsed:
        st.error("All models failed to generate picks.")

    # --- 4. Validate data format before saving to prevent crashes ---
    if parsed:
        if isinstance(parsed[0], dict):
            try:
                from .db import insert_ai_picks
                insert_ai_picks(parsed)
                st.toast(f"Saved {len(parsed)} new AI picks to history!")
            except Exception as e:
                st.error(f"Failed to save AI picks: {e}")
        else:
            st.warning(
                "AI returned unstructured data. Picks were displayed but not saved to history.")

    return parsed
