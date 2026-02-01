from datetime import datetime, timezone
import sqlite3
import os
from app.odds import american_to_probability


# Default DB path (persistent file)
DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "bets.db")
)


def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def get_most_recent_pick_timestamp(sport_name):
    """
    Finds the timestamp of the most recent AI pick for a given sport
    that is not in the future, returning a timezone-aware UTC object.
    """
    conn = get_db()
    cur = conn.cursor()

    # This query now ignores any picks with a date in the future,
    # preventing bad data from breaking the time-limit logic.
    now_utc_str = datetime.now(timezone.utc).isoformat()
    cur.execute(
        "SELECT MAX(date) FROM ai_picks WHERE sport = ? AND date <= ?",
        (sport_name, now_utc_str)
    )

    result = cur.fetchone()
    conn.close()

    if result and result[0]:
        date_str = result[0]
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
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
    conn = get_db()
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
    conn.close()


def insert_bet(team, opponent, market, stake=1, odds_american=None, probability=None, line=None):
    """Insert bet with EV/profit calculation, using American odds."""
    probability = american_to_probability(odds_american)
    profit = None

    if probability is not None:
        # EV calculation (expected value)
        profit = (probability - 0.5) * stake  # baseline: 50/50 fair coin

    conn = get_db()
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
    conn.close()


def list_bets(limit=50):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bets ORDER BY date DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# -------------------------
# AI Picks Table
# -------------------------


def init_ai_picks():
    """
    Ensures the ai_picks table exists and has the correct schema,
    including commence_time for accurate scheduling and source for tracking pick origin.
    """
    conn = get_db()
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
        print("⚠️ Adding missing column 'commence_time' to ai_picks table.")
        cur.execute("ALTER TABLE ai_picks ADD COLUMN commence_time TEXT")

    if 'source' not in existing_cols:
        print("⚠️ Adding missing column 'source' to ai_picks table.")
        cur.execute("ALTER TABLE ai_picks ADD COLUMN source TEXT DEFAULT 'AI'")

    conn.commit()
    conn.close()


def get_existing_picks():
    """
    Retrieves a set of all existing (pick, market) tuples from the database
    to quickly check for duplicates.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT pick, market FROM ai_picks")
    existing = set(cursor.fetchall())
    conn.close()
    return existing


def list_ai_picks(limit=50):
    """Return most recent AI picks from the database."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ai_picks ORDER BY date DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def insert_ai_picks(picks: list):
    """
    Batch inserts multiple AI picks, ensuring commence_time and source are saved correctly.
    """
    conn = get_db()
    cur = conn.cursor()

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

    cur.executemany("""
        INSERT INTO ai_picks (game, sport, pick, market, line, odds_american, confidence, reasoning, date, result, commence_time, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, picks_to_insert)

    conn.commit()
    conn.close()


def insert_ai_pick(pick: dict):
    """
    Insert a single AI pick, ensuring commence_time and source are saved correctly.
    Checks for duplicates before inserting.
    """
    conn = get_db()
    cur = conn.cursor()

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

    # Check if this exact pick already exists in database
    cur.execute("""
        SELECT id FROM ai_picks
        WHERE game = ? AND market = ? AND pick = ? AND line = ?
        LIMIT 1
    """, (game, market, pick_value, line_value))

    existing = cur.fetchone()
    if existing:
        print(
            f"⚠️ [insert_ai_pick] Duplicate pick detected: {game} - {pick_value} ({market})")
        conn.close()
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
    conn.close()
    return True


def fetch_performance_summary(sport_name):
    """
    Calculates and returns Win/Loss/Push/Units by confidence level for a given sport.
    """
    conn = get_db()
    cur = conn.cursor()

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

    cur.execute(query, (sport_name,))
    summary = [dict(row) for row in cur.fetchall()]
    conn.close()
    return summary


def get_unsettled_picks():
    """
    Fetches all picks from the ai_picks table that have a 'Pending' result.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM ai_picks WHERE result = 'Pending' OR result IS NULL")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_pick_result(pick_id, result):
    """
    Updates the 'result' column for a specific pick ID.
    Returns True if successful, False otherwise.
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE ai_picks SET result = ? WHERE id = ?",
            (result, pick_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating pick result: {e}")
        return False


def delete_ai_pick(pick_id):
    """
    Deletes a specific AI pick by ID.
    Returns True if successful, False otherwise.
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM ai_picks WHERE id = ?", (pick_id,))
        deleted_count = cur.rowcount
        conn.commit()
        conn.close()
        return deleted_count > 0
    except Exception as e:
        print(f"❌ Error deleting pick {pick_id}: {e}")
        return False
