import streamlit as st
import requests
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from openai import OpenAI
import google.generativeai as genai
from .db import get_db, init_ai_picks, insert_ai_picks
from .const import RAPIDAPI_KEY, HEADERS
from .utils.sport_config import SportConfig
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# --- Configure Gemini ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- Timezone Configuration ---
LOCAL_TZ_NAME = 'America/Los_Angeles'  # PST/PDT


def _safe_parse_datetime(date_str: str):
    """Safely parse ISO datetime to UTC datetime, return None if invalid."""
    if not date_str or str(date_str).strip().lower() in ("none", "<none>", "null", "", "nan"):
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def utc_to_local_display(utc_dt, format_str='%a, %b %d, %I:%M %p %Z'):
    """
    Convert UTC datetime to local timezone (PST/PDT) for display.

    Args:
        utc_dt: datetime object in UTC or ISO string
        format_str: strftime format string

    Returns:
        Formatted string in local timezone
    """
    if not utc_dt:
        return ""

    try:
        # Handle string input
        if isinstance(utc_dt, str):
            utc_dt = _safe_parse_datetime(utc_dt)
            if not utc_dt:
                return ""

        # Ensure timezone aware
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=timezone.utc)

        # Convert to local timezone
        local_tz = ZoneInfo(LOCAL_TZ_NAME)
        local_dt = utc_dt.astimezone(local_tz)

        return local_dt.strftime(format_str)
    except Exception:
        return str(utc_dt)

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


def fetch_historical_nhl(team_name, limit=None):
    """Fetch NHL historical games with optimized limit."""
    if limit is None:
        limit = SportConfig.get_historical_limit("icehockey_nhl")
    days = SportConfig.get_historical_days("icehockey_nhl")
    return _fetch_and_cache_historical_scores("icehockey_nhl", "NHL", team_name, limit, days)


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


def _call_claude_model(model_name, prompt):
    """Call Anthropic Claude model."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not set.")

    try:
        from anthropic import Anthropic
    except ImportError:
        raise ValueError(
            "anthropic package not installed. Run: pip install anthropic")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    # Claude requires explicit JSON formatting instruction
    json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON in this exact format: {{\"picks\": [...]}}"

    response = client.messages.create(
        model=model_name,
        max_tokens=4096,
        messages=[{"role": "user", "content": json_prompt}]
    )

    raw = response.content[0].text

    # Claude sometimes wraps JSON in markdown code blocks - strip them
    if raw.strip().startswith("```"):
        # Remove ```json or ``` from start and ``` from end
        lines = raw.strip().split('\n')
        if lines[0].startswith("```"):
            lines = lines[1:]  # Remove first line (```json or ```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove last line (```)
        raw = '\n'.join(lines)

    try:
        return json.loads(raw).get("picks", [])
    except Exception:
        return []

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

    2. **MARKET DIVERSITY GUIDELINE** (IMPORTANT):
       - **Prioritize consensus and confidence first** - don't sacrifice quality for diversity
       - However, avoid extreme concentration in one market (e.g., all 3 picks being totals)
       - If you have multiple high-confidence picks in the same market, consider including at least one pick from a different market
       - Ideal range: No single market should be >70% of picks (e.g., avoid 3/3 totals, but 2/3 totals is acceptable if consensus is strong)
       - **DO NOT force a 33/33/33 split** - let consensus drive the selection

    3. **CONSENSUS WEIGHTING** (CRITICAL):
       - **ONLY use sources that are EXPLICITLY present in the context data**
       - Available sources: "oddsshark", "oddstrader", "cbs_sports", "kalshi"
       - If 2+ sources agree on the SAME bet (same team, same market, similar line): **BOOST confidence by +1 star**
       - If 3+ sources agree: **BOOST confidence by +2 stars**

       **SOURCE CONFIDENCE BASELINES**:
       - **OddsTrader** (check `star_rating` field in data):
         * 4-star picks = High confidence baseline (can be 3 stars alone)
         * 3-star picks = Medium confidence baseline (needs another source for 3 stars)
         * Use the `star_rating` field from OddsTrader data to determine baseline
       - CBS Sports 5+ expert consensus = High confidence baseline
       - OddsShark computer pick = Medium confidence baseline

       **KALSHI AS PRIMARY SIGNAL** (NEW - HIGH PRIORITY):
       - **Kalshi Strong Signal** = (implied_prob > 0.65 OR implied_prob < 0.35) AND volume_24h > 500 AND open_interest > 2000
       - When Kalshi Strong Signal is present, **count it as a full source** (not just a boost)
       - Kalshi Strong Signal alone = 2.5 weighted sources (not enough for 3 stars, but close)
       - Kalshi Strong Signal + 1 other source = 3.5 weighted sources → **4 stars**
       - Kalshi Strong Signal + 2 other sources = 4.5 weighted sources → **5 stars**
       - Kalshi Medium Signal (volume_24h > 200, open_interest > 1000) = 0.5 boost (old behavior)

       **RANKING BOOST (NCAAB/NCAAF only)**:
       - Top 10 vs Top 10 matchup = +1 confidence boost (high-quality game)
       - Top 25 vs Top 25 matchup = +0.5 confidence boost
       - Ranked team favored by 10+ points over unranked = High confidence in favorite
       - Unranked team getting points vs Top 10 = Potential upset value

       **LINE VALUE ANALYSIS** (NEW - DETECT MARKET MISPRICING):
       - Compare consensus picks to DraftKings market lines to identify value
       - **Spread Value**: If consensus line is 2+ points better than DraftKings → +1 star boost
         * Example: Consensus says "Team A -3.5", DraftKings offers "Team A -1.5" → VALUE (getting extra 2 points)
         * Example: Consensus says "Team B +7.5", DraftKings offers "Team B +9.5" → VALUE (getting extra 2 points)
       - **Total Value**: If consensus line is 3+ points different from DraftKings → +1 star boost
         * Example: Consensus says "Over 220", DraftKings offers "Over 217" → VALUE (easier to hit over)
         * Example: Consensus says "Under 225", DraftKings offers "Under 228" → VALUE (easier to hit under)
       - **Moneyline Value**: If consensus pick has odds of +120 or better (underdog value) → +0.5 star boost
         * Rationale: Underdogs with consensus support offer better risk/reward
       - **IMPORTANT**: Only apply value boost if there's already at least 1 source supporting the pick

    4. **CONFIDENCE RATING SYSTEM** (CRITICAL - STRICT MINIMUM):

       **5 STARS** (Highest Confidence):
       - 3+ sources agree (strong consensus)
       - 2 sources + Kalshi Strong Signal
       - 2 sources + line value (2+ points for spreads, 3+ for totals)
       - OddsTrader 4-star + 2 other sources

       **4 STARS** (High Confidence):
       - 2 sources agree (any agreement)
       - 1 source + Kalshi Strong Signal
       - 1 source + Kalshi Strong Signal + line value
       - OddsTrader 4-star + 1 other source
       - OddsTrader 4-star + line value
       - OddsTrader 3-star + 2 other sources

       **3 STARS** (Medium Confidence - Minimum Threshold):
       - OddsTrader 4-star pick alone
       - 1 high-confidence source (CBS 5+ experts, OddsShark computer pick)
       - 1 high-confidence source + line value
       - OddsTrader 3-star + 1 other source
       - 2 medium sources agree

       **ABSOLUTE REQUIREMENT**: Only include picks with **3, 4, or 5 stars**
       - **DO NOT GENERATE 1 or 2 star picks** - they will be rejected
       - If no picks meet the 3+ star threshold, return an empty picks array

    5. **VALIDATION RULES** (CRITICAL - NO EXCEPTIONS):
       - Only select games where `commence_time` is in the future (not started)

       - **ODDS RANGE REQUIREMENT** (ABSOLUTE - NO EXCEPTIONS):
         * ❌ **REJECT ALL PICKS with odds outside +150 to -150 range**
         * ❌ **DO NOT recommend picks with odds like -200, -300, -425, +200, etc.**
         * ✅ **ONLY accept odds between +150 and -150** (e.g., -110, -135, +120, +145)
         * **WHY**: Heavy favorites (-200+) and long underdogs (+200+) have poor risk/reward
         * **ENFORCEMENT**: If a pick has odds outside this range, SKIP IT entirely
         * Examples of INVALID odds: -175, -200, -425, +160, +200, +300
         * Examples of VALID odds: -150, -135, -110, +100, +120, +150

       - **NO CONFLICTING PICKS**: Do NOT pick both sides of the same market for the same game
         * Example: Do NOT pick both "Over 43.5" AND "Under 43.5" for the same game
         * Example: Do NOT pick both "Team A -3.5" AND "Team B +3.5" for the same game
         * Example: Do NOT pick both "Team A ML" AND "Team B ML" for the same game

       - **MULTIPLE PICKS PER GAME ALLOWED**: You CAN pick multiple markets for the same game
         * Example: Pittsburgh -3 (spread) + Over 42.5 (total) for same game is ALLOWED
         * Example: Miami +3 (spread) + Miami ML (h2h) for same game is ALLOWED
         * Only restriction: Don't pick BOTH sides of the SAME market

       - Each pick MUST contain: "game", "sport", "pick", "market", "line", "odds_american", "confidence", "reasoning", "commence_time", "sources_agreeing"

    6. **OUTPUT FORMAT**:
       - "odds_american" must be numeric (e.g., -110, 150)
       - "commence_time" must be copied exactly from source in ISO format
       - "confidence" must be 3, 4, or 5 (integer) - **NEVER 1 or 2**
       - **"pick" field format** (CRITICAL - MUST FOLLOW EXACTLY):
         * For **spreads**: ONLY the team name, NO line value (e.g., "Tulane Green Wave" NOT "Tulane Green Wave +17.5")
         * For **totals**: ONLY "Over" or "Under", NO line value (e.g., "Over" NOT "Over 43.5")
         * For **h2h**: ONLY the team name (e.g., "Pittsburgh Steelers")
         * The line value goes in the separate "line" field, NOT in the "pick" field
         * Example CORRECT: {{"pick": "Tulane Green Wave", "line": 17.5, "market": "spreads"}}
         * Example WRONG: {{"pick": "Tulane Green Wave +17.5", "line": 17.5, "market": "spreads"}}
       - "sources_agreeing" must list ONLY sources that ACTUALLY appear in the context data for this specific game and pick
       - **DO NOT invent or hallucinate sources** - only list sources if they explicitly recommend this exact pick in the context
       - "reasoning" must be CONCISE (2-3 sentences max) and explain: (a) which sources agree, (b) why consensus is strong, (c) Kalshi sentiment if available, (d) for NCAAB/NCAAF: team rankings
       - **MASK SOURCE NAMES**: Use generic labels instead of specific names:
         * Replace "OddsShark" or "oddsshark" with "Consensus 1"
         * Replace "OddsTrader" or "oddstrader" with "Consensus 2"
         * Replace "CBS Sports" or "cbs_sports" with "Consensus 3"
         * Replace "DraftKings" with "Sportsbook"
         * Keep "Kalshi" as is (public prediction)
       - **DO NOT include** extraction dates, timestamps, or technical details in reasoning

    7. **PICK SELECTION STRATEGY**:
       - Return a maximum of 3 picks
       - **Prioritize highest consensus and confidence first**
       - If all 3 picks are from the same market AND there's a reasonable alternative from a different market (3+ stars), consider replacing the lowest confidence pick
       - Don't force diversity if consensus is clearly concentrated in one market
       - Example acceptable outputs:
         * 2 totals, 1 spread (if totals have stronger consensus)
         * 1 spread, 1 total, 1 h2h (balanced)
         * 3 totals (only if all are 5-star and no other markets have 4+ star picks)

    8. **FINAL VALIDATION BEFORE RETURNING** (MANDATORY CHECKLIST):
       - Review each pick's confidence rating
       - **REMOVE any picks with confidence < 3**
       - **REMOVE any picks with odds outside +150 to -150 range**
         * Check EVERY pick: Is -150 ≤ odds ≤ +150?
         * If NO, DELETE that pick immediately
         * Examples to DELETE: -175, -200, -425, +160, +200, +300
       - **REMOVE any conflicting picks** (both sides of same game/market)
       - If this leaves you with 0 picks, return {{"picks": []}}
       - Better to return no picks than picks that violate the rules

    Context: {json.dumps(context, indent=2)}
    """

    # Model priority order: Best reasoning → Fast fallback → Emergency fallback
    models = [
        # Tier 1: Best reasoning and analysis (Primary)
        {'provider': 'anthropic', 'name': 'claude-sonnet-4-5'},
        {'provider': 'google', 'name': 'gemini-2.5-pro'},
        {'provider': 'openai', 'name': 'gpt-5'},

        # Tier 2: Fast and cost-effective (Fallback)
        {'provider': 'anthropic', 'name': 'claude-haiku-4-5-20251001'},
        {'provider': 'google', 'name': 'gemini-2.5-flash'},
        {'provider': 'openai', 'name': 'gpt-5-mini'},

        # Tier 3: Ultra-fast emergency fallback
        {'provider': 'openai', 'name': 'gpt-5-nano'},
        {'provider': 'google', 'name': 'gemini-2.5-flash-lite'},
    ]

    parsed = []
    for m in models:
        try:
            # Call appropriate model based on provider
            if m['provider'] == 'google':
                parsed = _call_gemini_model(m['name'], prompt)
            elif m['provider'] == 'openai':
                parsed = _call_openai_model(m['name'], prompt)
            elif m['provider'] == 'anthropic':
                parsed = _call_claude_model(m['name'], prompt)
            else:
                st.warning(f"Unknown provider: {m['provider']}")
                continue

            if parsed:
                st.success(
                    f"✅ Generated {len(parsed)} picks using {m['provider']}:{m['name']}")
                break
        except Exception as e:
            st.warning(
                f"⚠️ {m['provider']}:{m['name']} failed: {str(e)[:100]}")
            continue

    if not parsed:
        st.error("All models failed to generate picks.")
        return []

    # Get existing picks from database to avoid duplicates and conflicts
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT game, market, pick, line FROM ai_picks
        WHERE result = 'Pending'
        AND datetime(commence_time) > datetime('now')
    """)
    existing_picks = set()
    existing_game_markets = {}  # Track picks by game+market
    for row in cur.fetchall():
        game = row[0].strip() if row[0] else ""
        market = row[1].strip() if row[1] else ""
        pick = row[2].strip() if row[2] else ""
        line = row[3]

        # Track full pick signature for exact duplicates
        existing_picks.add((game, market, pick, line))

        # Track picks by game+market for conflict detection
        key = (game, market)
        if key not in existing_game_markets:
            existing_game_markets[key] = []
        existing_game_markets[key].append((pick, line))
    conn.close()

    unique_picks = []
    seen_game_markets = {}  # Track picks in current batch by game+market
    skipped_duplicates = 0
    skipped_conflicts = 0

    def normalize_pick_team(pick_str, line_val):
        """
        Normalize a pick string to extract just the team name.
        Handles cases like:
        - "Tulane Green Wave +17.5" -> "tulane green wave"
        - "Tulane Green Wave" -> "tulane green wave"
        - "Ole Miss Rebels -3.5" -> "ole miss rebels"
        """
        import re
        pick_normalized = pick_str.lower().strip()

        # Remove line value if present (e.g., "+17.5", "-3.5", "17.5")
        if line_val is not None:
            # Try to remove the line in various formats
            patterns = [
                # " +17.5" or " -17.5" at end
                rf'\s*\+?\-?{re.escape(str(line_val))}\s*$',
                # " +17.5" at end
                rf'\s*\+{re.escape(str(abs(float(line_val))))}\s*$',
                # " -17.5" at end
                rf'\s*\-{re.escape(str(abs(float(line_val))))}\s*$',
            ]
            for pattern in patterns:
                pick_normalized = re.sub(pattern, '', pick_normalized)

        # Remove any remaining +/- signs at the end
        pick_normalized = re.sub(r'\s*[\+\-]\s*$', '', pick_normalized)

        return pick_normalized.strip()

    def is_conflicting_pick(game, market, pick_value, line, existing_picks_list):
        """Check if a pick conflicts with existing picks for the same game+market."""
        market_lower = market.lower()
        pick_lower = pick_value.lower()

        for existing_pick, existing_line in existing_picks_list:
            existing_pick_lower = existing_pick.lower()

            # Spread: Can't pick both teams (opposite signs) OR same team with same/similar line
            if market_lower == 'spreads':
                try:
                    new_line_val = float(str(line).replace('+', ''))
                    existing_line_val = float(
                        str(existing_line).replace('+', ''))

                    # Normalize team names by removing line info
                    new_team = normalize_pick_team(pick_value, line)
                    existing_team = normalize_pick_team(
                        existing_pick, existing_line)

                    # If same team with same line value (regardless of sign), it's a duplicate
                    if new_team == existing_team and abs(new_line_val) == abs(existing_line_val):
                        return True

                    # If lines have opposite signs, it's a conflict (picking both sides)
                    if (new_line_val > 0 and existing_line_val < 0) or (new_line_val < 0 and existing_line_val > 0):
                        return True
                except (ValueError, TypeError):
                    pass

            # Totals: Can't pick both Over AND Under
            elif market_lower == 'totals':
                if (pick_lower == 'over' and existing_pick_lower == 'under') or \
                   (pick_lower == 'under' and existing_pick_lower == 'over'):
                    return True

            # H2H/Moneyline: Can't pick both teams
            elif market_lower == 'h2h':
                # If picks are different teams, it's a conflict
                if pick_lower != existing_pick_lower:
                    return True

        return False

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

        # Check for conflicts with existing picks in database (same game+market)
        game_market_key = (game, market)
        if game_market_key in existing_game_markets:
            if is_conflicting_pick(game, market, pick_value, line, existing_game_markets[game_market_key]):
                skipped_conflicts += 1
                continue

        # Check for conflicts with picks already added in current batch
        if game_market_key in seen_game_markets:
            if is_conflicting_pick(game, market, pick_value, line, seen_game_markets[game_market_key]):
                skipped_conflicts += 1
                continue

        # Add to current batch tracking
        if game_market_key not in seen_game_markets:
            seen_game_markets[game_market_key] = []
        seen_game_markets[game_market_key].append((pick_value, line))

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


def _check_pick_result(pick_dict, home_score, away_score):
    """
    Determines if a single pick (H2H, Spread, or Total) won, lost, or pushed.
    Returns 'Win', 'Loss', 'Push', or 'Pending'.

    Args:
        pick_dict: Dictionary with keys: 'pick', 'market', 'line'
        home_score: Integer home team score
        away_score: Integer away team score
    """
    if home_score is None or away_score is None:
        return 'Pending'

    market = pick_dict.get('market', '').lower()

    # Handle h2h (moneyline)
    if market == 'h2h':
        game = pick_dict.get('game', '')
        if ' @ ' not in game:
            return 'Pending'

        away_team, home_team = game.split(' @ ')

        if home_score > away_score:
            winner = home_team
        elif away_score > home_score:
            winner = away_team
        else:
            return 'Push'

        return 'Win' if pick_dict['pick'] == winner else 'Loss'

    # Handle spreads
    elif market == 'spreads':
        line = pick_dict.get('line')
        if line is None:
            return 'Pending'

        game = pick_dict.get('game', '')
        if ' @ ' not in game:
            return 'Pending'

        away_team, home_team = game.split(' @ ')

        # Determine if pick is for home or away team
        if pick_dict['pick'] == home_team:
            adjusted_score = home_score + line
            opponent_score = away_score
        elif pick_dict['pick'] == away_team:
            adjusted_score = away_score + line
            opponent_score = home_score
        else:
            return 'Pending'

        if adjusted_score > opponent_score:
            return 'Win'
        elif adjusted_score < opponent_score:
            return 'Loss'
        else:
            return 'Push'

    # Handle totals (over/under)
    elif market == 'totals':
        line = pick_dict.get('line')
        if line is None:
            return 'Pending'

        total_score = home_score + away_score
        pick = pick_dict.get('pick', '').lower()

        if pick == 'over':
            if total_score > line:
                return 'Win'
            elif total_score < line:
                return 'Loss'
            else:
                return 'Push'
        elif pick == 'under':
            if total_score < line:
                return 'Win'
            elif total_score > line:
                return 'Loss'
            else:
                return 'Push'

    return 'Pending'


def update_ai_pick_results():
    conn = get_db()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, game, pick, market, line, sport, commence_time FROM ai_picks WHERE LOWER(result)='pending'")
    pending = cur.fetchall()
    if not pending:
        print("No pending picks to update.")
        conn.close()
        return

    print(f"🔍 Checking {len(pending)} pending picks...")
    updated = 0
    skipped_not_started = 0
    skipped_not_completed = 0

    for row in pending:
        commence = row["commence_time"]
        dt = _safe_parse_datetime(commence)
        if not dt:
            print(
                f"⚠️ Could not parse commence_time for pick {row['id']}: {commence}")
            continue

        # Skip games that haven't started yet
        if datetime.now(timezone.utc) < dt:
            skipped_not_started += 1
            continue

        # Extract the date from the pick's commence_time (YYYY-MM-DD)
        pick_date = dt.strftime('%Y-%m-%d')

        # Map sport name to API key
        sport = row["sport"]
        if sport == "NFL":
            sport_key = "americanfootball_nfl"
        elif sport == "NCAAF":
            sport_key = "americanfootball_ncaaf"
        elif sport == "NCAAB":
            sport_key = "basketball_ncaab"
        elif sport == "NBA":
            sport_key = "basketball_nba"
        elif sport == "NHL":
            sport_key = "icehockey_nhl"
        else:
            continue

        try:
            scores = fetch_scores(sport=sport_key, days_from=2)
        except Exception as e:
            print(f"⚠️ Failed to fetch scores for {sport}: {e}")
            continue

        for g in scores:
            # CRITICAL: Only process completed games
            if not g.get("completed"):
                continue

            # Match by team names
            if g.get("home_team") in row["game"] and g.get("away_team") in row["game"]:
                # CRITICAL: Also match by date to prevent scoring wrong games
                game_commence = g.get("commence_time", "")
                game_date = game_commence[:10]  # Extract YYYY-MM-DD

                if game_date != pick_date:
                    print(
                        f"⚠️ Date mismatch for {row['game']}: pick={pick_date}, game={game_date}")
                    continue

                home, away = g["home_team"], g["away_team"]
                hs = next((s["score"]
                          for s in g["scores"] if s["name"] == home), None)
                as_ = next((s["score"]
                           for s in g["scores"] if s["name"] == away), None)
                if hs is None or as_ is None:
                    print(
                        f"⚠️ Missing scores for {row['game']}: home={hs}, away={as_}")
                    continue

                # Convert to dict for helper function
                pick_dict = {
                    'game': row['game'],
                    'pick': row['pick'],
                    'market': row['market'],
                    'line': row['line']
                }

                result = _check_pick_result(pick_dict, int(hs), int(as_))

                if result != 'Pending':
                    print(
                        f"✅ Scoring pick {row['id']}: {row['game']} - {row['pick']} ({row['market']}) = {result}")
                    cur.execute("UPDATE ai_picks SET result=? WHERE id=?",
                                (result, row["id"]))
                    updated += 1
                else:
                    print(f"⚠️ Result still pending for {row['game']}")
                break

    conn.commit()
    conn.close()
    print(
        f"✅ Updated {updated} picks. Skipped {skipped_not_started} not started, {skipped_not_completed} not completed.")
