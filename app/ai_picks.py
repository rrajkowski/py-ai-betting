import streamlit as st
import requests
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from openai import OpenAI
import google.generativeai as genai
from .db import get_db, init_ai_picks, insert_ai_picks
from .const import RAPIDAPI_KEY, HEADERS
from .utils.sport_config import SportConfig
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def _safe_parse_datetime(date_str: str):
    """Safely parse ISO datetime to UTC datetime, return None if invalid."""
    if not date_str or str(date_str).strip().lower() in ("none", "<none>", "null", "", "nan"):
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None

# -------------------------
# DB Migration for historical_games
# -------------------------


def migrate_historical_games():
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
    Fetch odds from RapidAPI with seasonal awareness and 3-day filtering.

    Args:
        sport: Sport key (e.g., 'americanfootball_nfl')

    Returns:
        List of upcoming games with odds (next 3 days only)
    """
    # Check if sport is in season
    if not SportConfig.is_in_season(sport):
        print(f"📊 Odds API: Skipping {sport.upper()} - out of season")
        return []

    url = f"https://odds.p.rapidapi.com/v4/sports/{sport}/odds"
    querystring = {
        "regions": "us", "oddsFormat": "american",
        "markets": "h2h,spreads,totals", "dateFormat": "iso"
    }
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": "odds.p.rapidapi.com"
    }

    try:
        r = requests.get(url, headers=headers, params=querystring, timeout=15)
        r.raise_for_status()
        all_games = r.json()
    except requests.exceptions.Timeout:
        print(f"❌ Odds API timeout for {sport}")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"❌ Odds API HTTP error for {sport}: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"❌ Odds API error for {sport}: {e}")
        return []

    now_utc = datetime.now(timezone.utc)
    max_future_date = now_utc + timedelta(days=3)  # Only next 3 days
    future_games = []

    for game in all_games:
        dt = _safe_parse_datetime(game.get('commence_time'))
        if dt and now_utc < dt <= max_future_date:  # Filter to 3-day window
            game['commence_time'] = dt.isoformat()
            future_games.append(game)

    print(
        f"📊 Odds API: Found {len(future_games)}/{len(all_games)} upcoming games for {SportConfig.get_sport_name(sport)}")
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
        dt = _safe_parse_datetime(game.get('commence_time'))
        if not dt:
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
            "date": dt.isoformat(),
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


def fetch_historical_ncaaf(team_name, limit=None):
    """Fetch NCAAF historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("americanfootball_ncaaf")
    days = SportConfig.get_historical_days("americanfootball_ncaaf")
    return _fetch_and_cache_historical_scores("americanfootball_ncaaf", "NCAAF", team_name, limit, days)


def fetch_historical_nfl(team_name, limit=None):
    """Fetch NFL historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("americanfootball_nfl")
    days = SportConfig.get_historical_days("americanfootball_nfl")
    return _fetch_and_cache_historical_scores("americanfootball_nfl", "NFL", team_name, limit, days)


# def fetch_historical_mlb(team_name, limit=None):  # Season over
#     """Fetch MLB historical games with optimized limit."""
#     if limit is None:
#         limit = SportConfig.get_historical_limit("baseball_mlb")
#     days = SportConfig.get_historical_days("baseball_mlb")
#     return _fetch_and_cache_historical_scores("baseball_mlb", "MLB", team_name, limit, days)


def fetch_historical_ncaab(team_name, limit=None):
    """Fetch NCAAB historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("basketball_ncaab")
    days = SportConfig.get_historical_days("basketball_ncaab")
    return _fetch_and_cache_historical_scores("basketball_ncaab", "NCAAB", team_name, limit, days)


def fetch_historical_nba(team_name, limit=None):
    """Fetch NBA historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("basketball_nba")
    days = SportConfig.get_historical_days("basketball_nba")
    return _fetch_and_cache_historical_scores("basketball_nba", "NBA", team_name, limit, days)


def fetch_historical_other(team_name, limit=10):
    return []

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
    resp_json = json.loads(resp.text)
    if isinstance(resp_json, list):
        parsed = resp_json
    else:
        parsed = resp_json.get("picks", [])
    return parsed

# -------------------------
# Generate AI Picks
# -------------------------


def generate_ai_picks(odds_df, history_data, sport="unknown", context_payload=None, kalshi_context=None):
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
    You are a hyper-efficient sports betting analyst. Your goal is to quickly identify the best value bets using multi-source consensus.

    Instructions:
    1. Analyze the provided context, including:
       - Odds from DraftKings
       - Historical performance data
       - Kalshi sentiment data (popularity_score, volume_24h, open_interest)
       - Expert consensus from multiple sources (OddsShark, OddsTrader, CBS Sports)
       - Team rankings (NCAAB/NCAAF): AP Poll, Coaches Poll, CBS Rankings

    2. **CONSENSUS WEIGHTING** (CRITICAL):
       - **ONLY use sources that are EXPLICITLY present in the context data**
       - Available sources: "oddsshark", "oddstrader", "cbs_sports", "kalshi"
       - If 2+ sources agree on the SAME bet (same team, same market, similar line): **BOOST confidence by +1 star**
       - If 3+ sources agree: **BOOST confidence by +2 stars**
       - OddsTrader 4-star picks = High confidence baseline
       - CBS Sports 5+ expert consensus = High confidence baseline
       - Kalshi high volume (>1000) + high open interest (>5000) = Medium confidence boost
       - **RANKING BOOST (NCAAB/NCAAF only)**:
         * Top 10 vs Top 10 matchup = +1 confidence boost (high-quality game)
         * Top 25 vs Top 25 matchup = +0.5 confidence boost
         * Ranked team favored by 10+ points over unranked = High confidence in favorite
         * Unranked team getting points vs Top 10 = Potential upset value

    3. **CONFIDENCE RATING SYSTEM**:
       - 5 stars: 3+ sources agree OR 2 sources + strong Kalshi sentiment
       - 4 stars: 2 sources agree OR 1 high-confidence source + Kalshi boost
       - 3 stars: 1 high-confidence source OR multiple medium sources
       - Only include picks with **3, 4, or 5 stars**

    4. **VALIDATION RULES** (CRITICAL - NO EXCEPTIONS):
       - Only select games where `commence_time` is in the future (not started)
       - **NO CONFLICTING PICKS**: Do NOT pick both sides of the same market for the same game
         * Example: Do NOT pick both "Over 43.5" AND "Under 43.5" for the same game
         * Example: Do NOT pick both "Team A -3.5" AND "Team B +3.5" for the same game
         * Example: Do NOT pick both "Team A ML" AND "Team B ML" for the same game
       - **ONE PICK PER GAME MAXIMUM**: Each game should have at most ONE pick
       - Exclude odds outside the range (+150 to -150)
       - Each pick MUST contain: "game", "sport", "pick", "market", "line", "odds_american", "confidence", "reasoning", "commence_time", "sources_agreeing"

    5. **OUTPUT FORMAT**:
       - "odds_american" must be numeric (e.g., -110, 150)
       - "commence_time" must be copied exactly from source in ISO format
       - "confidence" must be 3, 4, or 5 (integer)
       - "sources_agreeing" must list ONLY sources that ACTUALLY appear in the context data for this specific game and pick
       - **DO NOT invent or hallucinate sources** - only list sources if they explicitly recommend this exact pick in the context
       - "reasoning" must be CONCISE (2-3 sentences max) and explain: (a) which sources agree, (b) why consensus is strong, (c) Kalshi sentiment if available, (d) for NCAAB/NCAAF: team rankings
       - **MASK SOURCE NAMES**: Use generic labels instead of specific names:
         * Replace "OddsShark" or "oddsshark" with "Consensus Source 1"
         * Replace "OddsTrader" or "oddstrader" with "Consensus Source 2"
         * Replace "CBS Sports" or "cbs_sports" with "Consensus Source 3"
         * Replace "DraftKings" with "Sportsbook"
         * Keep "Kalshi" as is (public prediction market)
       - **DO NOT include** extraction dates, timestamps, or technical details in reasoning

    6. Return a maximum of 3 picks, prioritizing highest consensus first.

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
            parsed = _call_gemini_model(
                m['name'], prompt) if m['provider'] == 'google' else _call_openai_model(m['name'], prompt)
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

    # Get existing picks from database to avoid duplicates
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT game, market, pick, line FROM ai_picks
        WHERE result = 'Pending'
        AND datetime(commence_time) > datetime('now')
    """)
    existing_picks = set()
    existing_games = set()
    for row in cur.fetchall():
        game = row[0].strip() if row[0] else ""
        market = row[1].strip() if row[1] else ""
        pick = row[2].strip() if row[2] else ""
        line = row[3]

        # Track full pick signature
        existing_picks.add((game, market, pick, line))
        # Track games that already have picks
        existing_games.add(game)
    conn.close()

    unique_picks, seen_games = [], set()
    skipped_duplicates = 0
    skipped_conflicts = 0

    for pick in parsed:
        pick.setdefault("sport", sport)
        dt = _safe_parse_datetime(
            pick.get('commence_time') or pick.get('date'))
        if not dt:
            st.warning(
                f"⏰ Missing commence_time for {pick.get('game')}, defaulting to now()")
            dt = datetime.now(timezone.utc)
            pick['commence_time'] = dt.isoformat()

        try:
            if int(pick.get("confidence", 0)) < 3:
                continue
        except (ValueError, TypeError):
            continue

        game = pick.get('game', '').strip()
        market = pick.get('market', '').strip()
        pick_value = pick.get('pick', '').strip()
        line = pick.get('line')

        # Check if this exact pick already exists in database
        pick_signature = (game, market, pick_value, line)
        if pick_signature in existing_picks:
            skipped_duplicates += 1
            continue

        # Check if this game already has a pick in database
        if game in existing_games:
            skipped_conflicts += 1
            continue

        # Check if we've already added a pick for this game in current batch
        if game in seen_games:
            skipped_conflicts += 1
            continue

        seen_games.add(game)
        unique_picks.append(pick)

    if skipped_duplicates > 0:
        st.info(
            f"⏭️ Skipped {skipped_duplicates} duplicate pick(s) already in database")
    if skipped_conflicts > 0:
        st.info(
            f"⏭️ Skipped {skipped_conflicts} conflicting pick(s) for games with existing picks")

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
        commence = row["commence_time"]
        dt = _safe_parse_datetime(commence)
        if not dt:
            continue
        if datetime.now(timezone.utc) < dt:
            continue

        sport = row["sport"].lower().replace(" ", "_")
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
                elif (row["pick"] == home and int(hs) > int(as_)) or (row["pick"] == away and int(as_) > int(hs)):
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
