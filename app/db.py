import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime

from app.odds import american_to_probability

logger = logging.getLogger(__name__)


# Railway-aware database path configuration
# Railway uses /app for code; we mount the volume to /app/data for persistence
PERSISTENT_DIR = "/app/data" if os.getenv("RAILWAY_ENVIRONMENT") else "."

# Ensure the directory exists (important for local development)
if not os.path.exists(PERSISTENT_DIR):
    os.makedirs(PERSISTENT_DIR)

# Default DB path (persistent file)
DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(PERSISTENT_DIR, "bets.db")
)

CONTEXT_TABLE = "prompt_context"


@contextmanager
def get_db():
    """
    Context manager for SQLite database connections.
    Ensures connections are always closed, even if an exception occurs.
    Enables WAL mode for better concurrent read/write performance.

    Usage:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(...)
    """
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def get_most_recent_pick_timestamp(sport_name):
    """
    Finds the timestamp of the most recent AI pick for a given sport
    that is not in the future, returning a timezone-aware UTC object.
    """
    with get_db() as conn:
        cur = conn.cursor()

        # This query now ignores any picks with a date in the future,
        # preventing bad data from breaking the time-limit logic.
        now_utc_str = datetime.now(UTC).isoformat()
        cur.execute(
            "SELECT MAX(date) FROM ai_picks WHERE sport = ? AND date <= ?",
            (sport_name, now_utc_str)
        )

        result = cur.fetchone()

    if result and result[0]:
        date_str = result[0]
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt

    return None


def normalize_line(value):
    """Convert line values to float or None (handles 'ML' or bad input)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

# -------------------------
# Bets Table
# -------------------------


def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team TEXT NOT NULL,
                opponent TEXT NOT NULL,
                market TEXT NOT NULL,
                stake REAL DEFAULT 50.0,
                odds REAL,
                odds_american INTEGER,
                line REAL,
                probability REAL,
                profit REAL,
                date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def insert_bet(team, opponent, market, stake=1, odds_american=None, probability=None, line=None):
    """Insert bet with EV/profit calculation, using American odds."""
    probability = american_to_probability(odds_american)
    profit = None

    if probability is not None:
        # EV calculation (expected value)
        profit = (probability - 0.5) * stake  # baseline: 50/50 fair coin

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO bets (team, opponent, market, stake, odds_american, probability, profit, line)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            team,
            opponent,
            market,
            stake,
            odds_american,
            probability,
            profit,
            line,
        ))
        conn.commit()


def list_bets(limit=50):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM bets ORDER BY date DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
    return rows

# -------------------------
# AI Picks Table
# -------------------------


def init_ai_picks():
    """
    Ensures the ai_picks table exists and has the correct schema,
    including commence_time for accurate scheduling and source for tracking pick origin.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_picks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game TEXT,
                sport TEXT,
                pick TEXT,
                market TEXT,
                line REAL,
                odds_american REAL,
                confidence TEXT,
                reasoning TEXT,
                date TEXT,
                result TEXT DEFAULT 'Pending',
                commence_time TEXT,
                source TEXT DEFAULT 'AI'
            )
        """)

        cur.execute("PRAGMA table_info(ai_picks)")
        existing_cols = {row['name'] for row in cur.fetchall()}

        if 'commence_time' not in existing_cols:
            logger.warning(
                "Adding missing column 'commence_time' to ai_picks table.")
            cur.execute("ALTER TABLE ai_picks ADD COLUMN commence_time TEXT")

        if 'source' not in existing_cols:
            logger.warning("Adding missing column 'source' to ai_picks table.")
            cur.execute(
                "ALTER TABLE ai_picks ADD COLUMN source TEXT DEFAULT 'AI'")

        conn.commit()


def get_existing_picks():
    """
    Retrieves a set of all existing (pick, market) tuples from the database
    to quickly check for duplicates.
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pick, market FROM ai_picks")
        existing = set(cursor.fetchall())
    return existing


def list_ai_picks(limit=50):
    """Return most recent AI picks from the database."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_picks ORDER BY date DESC LIMIT ?", (limit,))
        rows = [dict(r) for r in cur.fetchall()]
    return rows


def insert_ai_picks(picks: list):
    """
    Batch inserts multiple AI picks, ensuring commence_time and source are saved correctly.
    """
    picks_to_insert = []
    for p in picks:
        try:
            line = float(p.get("line"))
        except (TypeError, ValueError):
            line = None

        try:
            odds = float(p.get("odds_american"))
        except (TypeError, ValueError):
            odds = None

        commence_time = p.get("commence_time")
        source = p.get("source", "AI")  # Default to AI if not specified

        picks_to_insert.append((
            p.get("game"), p.get("sport"), p.get("pick"), p.get("market"),
            line, odds, p.get("confidence"), p.get("reasoning"),
            commence_time,  # Use commence_time for the 'date' field
            p.get("result", "Pending"),
            commence_time,
            source
        ))

    with get_db() as conn:
        cur = conn.cursor()
        cur.executemany("""
            INSERT INTO ai_picks (game, sport, pick, market, line, odds_american, confidence, reasoning, date, result, commence_time, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, picks_to_insert)
        conn.commit()


def insert_ai_pick(pick: dict):
    """
    Insert a single AI pick, ensuring commence_time and source are saved correctly.
    Checks for duplicates before inserting.
    """
    try:
        line_value = float(pick.get("line"))
    except (TypeError, ValueError):
        line_value = None

    try:
        odds_value = float(pick.get("odds_american"))
    except (TypeError, ValueError):
        odds_value = None

    game = pick.get("game", "").strip()
    market = pick.get("market", "").strip()
    pick_value = pick.get("pick", "").strip()

    with get_db() as conn:
        cur = conn.cursor()

        # Check if this exact pick already exists in database
        cur.execute("""
            SELECT id FROM ai_picks
            WHERE game = ? AND market = ? AND pick = ? AND line = ?
            LIMIT 1
        """, (game, market, pick_value, line_value))

        existing = cur.fetchone()
        if existing:
            logger.warning(
                f"[insert_ai_pick] Duplicate pick detected: {game} - {pick_value} ({market})")
            return False

        commence_time = pick.get("commence_time")
        source = pick.get("source", "AI")  # Default to AI if not specified

        cur.execute("""
            INSERT INTO ai_picks (game, sport, pick, market, line, odds_american, confidence, reasoning, date, result, commence_time, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game,
            pick.get("sport"),
            pick_value,
            market,
            line_value,
            odds_value,
            pick.get("confidence"),
            pick.get("reasoning"),
            commence_time,  # Use commence_time for the 'date' field
            pick.get("result", "Pending"),
            commence_time,
            source,
        ))

        conn.commit()
    return True


def fetch_performance_summary(sport_name):
    """
    Calculates and returns Win/Loss/Push/Units by confidence level for a given sport.
    """
    query = """
    SELECT
        SUBSTR(confidence, 1, 1) AS star_rating,
        SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) AS total_wins,
        SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) AS total_losses,
        SUM(CASE WHEN result = 'Push' THEN 1 ELSE 0 END) AS total_pushes,
        SUM(
            CASE
                WHEN result = 'Win' AND odds_american > 0 THEN (odds_american / 100.0)
                WHEN result = 'Win' AND odds_american < 0 THEN (100.0 / ABS(odds_american))
                WHEN result = 'Loss' THEN -1.0
                ELSE 0
            END
        ) AS net_units
    FROM
        ai_picks
    WHERE
        sport = ? AND result IN ('Win', 'Loss', 'Push')
    GROUP BY
        star_rating
    ORDER BY
        star_rating DESC;
    """

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(query, (sport_name,))
        summary = [dict(row) for row in cur.fetchall()]
    return summary


def get_unsettled_picks():
    """
    Fetches all picks from the ai_picks table that have a 'Pending' result.
    """
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM ai_picks WHERE result = 'Pending' OR result IS NULL")
        rows = [dict(r) for r in cur.fetchall()]
    return rows


def update_pick_result(pick_id, result):
    """
    Updates the 'result' column for a specific pick ID.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE ai_picks SET result = ? WHERE id = ?",
                (result, pick_id)
            )
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating pick result: {e}")
        return False


def delete_ai_pick(pick_id):
    """
    Deletes a specific AI pick by ID.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM ai_picks WHERE id = ?", (pick_id,))
            deleted_count = cur.rowcount
            conn.commit()
        return deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting pick {pick_id}: {e}")
        return False


# -------------------------
# Prompt Context Table
# -------------------------


def init_prompt_context_db():
    """
    Creates the unified prompt_context table if it does not exist.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {CONTEXT_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,        -- "storage" or "realtime"
                context_type TEXT NOT NULL,    -- e.g. "expert_consensus", "public_consensus"
                game_id TEXT NOT NULL,         -- e.g. "NFL2025-WK5-KCvsBUF"
                match_date TEXT NOT NULL,      -- YYYY-MM-DD
                sport TEXT,                    -- Sport filter column (e.g., 'NFL')
                team_pick TEXT,
                data TEXT NOT NULL,           -- Stored as JSON string
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # --- Schema migration: Add 'sport' column if missing ---
        cur.execute(f"PRAGMA table_info({CONTEXT_TABLE})")
        cols = {row['name'] for row in cur.fetchall()}
        if "sport" not in cols:
            cur.execute(
                f"ALTER TABLE {CONTEXT_TABLE} ADD COLUMN sport TEXT")

        conn.commit()
    logger.info(f"Unified context database '{CONTEXT_TABLE}' initialized.")


def insert_context(category: str, context_type: str, game_id: str, match_date: str, sport: str, data: dict, source: str, team_pick: str | None = None):
    """
    Inserts a single row of context data into the prompt_context table.
    Data object is serialized to JSON string before insertion.
    """
    with get_db() as conn:
        cur = conn.cursor()

        cur.execute(f"""
            INSERT INTO {CONTEXT_TABLE} (category, context_type, game_id, match_date, sport, team_pick, data, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            category,
            context_type,
            game_id,
            match_date,
            sport,
            team_pick,
            json.dumps(data),
            source
        ))
        conn.commit()


def fetch_context_by_date(match_date: str, sport: str):
    """
    Fetches all context records for upcoming games (next 3 days) for a specific sport.
    Returns a list of dictionaries with 'data' decoded from JSON.
    Includes debug logging to help diagnose context issues.

    Args:
        match_date: Date string in YYYY-MM-DD format (used as starting point)
        sport: Sport key (e.g., 'americanfootball_nfl' or 'NFL')
    """
    from datetime import timedelta

    with get_db() as conn:
        cur = conn.cursor()

        # Convert sport key to uppercase sport name if needed
        # e.g., 'americanfootball_nfl' -> 'NFL', 'basketball_ncaab' -> 'NCAAB'
        if '_' in sport:
            sport_name = sport.split('_')[-1].upper()
        else:
            sport_name = sport.upper()

        # Debug: Check what sports are in the database
        cur.execute(f"SELECT DISTINCT sport FROM {CONTEXT_TABLE}")
        available_sports = [row[0] for row in cur.fetchall()]
        logger.debug(
            f"DB Debug: Available sports in database: {available_sports}")

        # Debug: Check what dates are in the database for this sport
        cur.execute(
            f"SELECT DISTINCT substr(match_date, 1, 10) as date FROM {CONTEXT_TABLE} WHERE sport = ?", (sport_name,))
        available_dates = [row[0] for row in cur.fetchall()]
        # Show first 5
        logger.debug(
            f"DB Debug: Available dates for {sport_name}: {available_dates[:5]}...")

        # Calculate date range: today through next 3 days
        start_date = datetime.strptime(match_date, '%Y-%m-%d')
        end_date = start_date + timedelta(days=3)
        end_date_str = end_date.strftime('%Y-%m-%d')

        logger.debug(
            f"DB Debug: Looking for games between {match_date} and {end_date_str}")

        # Main query - Get all games in the next 3 days
        # Use substr to extract date from timestamps like "2025-11-09T14:30:00Z"
        cur.execute(f"""
            SELECT * FROM {CONTEXT_TABLE}
            WHERE sport = ?
            AND substr(match_date, 1, 10) >= ?
            AND substr(match_date, 1, 10) <= ?
        """, (sport_name, match_date, end_date_str))

        rows = [dict(r) for r in cur.fetchall()]

        # Debug: Show breakdown by context_type and source
        if rows:
            context_types = {}
            sources = {}
            for row in rows:
                ct = row.get('context_type', 'unknown')
                src = row.get('source', 'unknown')
                context_types[ct] = context_types.get(ct, 0) + 1
                sources[src] = sources.get(src, 0) + 1
            logger.debug(f"DB Debug: Context types found: {context_types}")
            logger.debug(f"DB Debug: Sources found: {sources}")
        else:
            logger.warning(
                f"DB Debug: No records found for sport='{sport_name}' between {match_date} and {end_date_str}")

    for row in rows:
        try:
            row['data'] = json.loads(row['data'])
        except (TypeError, json.JSONDecodeError):
            row['data'] = {}

    return rows
