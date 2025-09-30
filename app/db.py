from datetime import datetime
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
    Finds the timestamp of the most recent AI pick for a given sport.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT MAX(date) FROM ai_picks WHERE sport = ?",
        (sport_name,)
    )
    result = cur.fetchone()
    conn.close()
    if result and result[0]:
        # Convert string timestamp from DB back to a datetime object
        return datetime.fromisoformat(result[0])
    return None


def normalize_line(value):
    """Convert line values to float or None (handles 'ML' or bad input)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def migrate_ai_picks():
    """Ensure ai_picks has all expected columns."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(ai_picks)")
    cols = [r[1] for r in cur.fetchall()]
    if "sport" not in cols:
        cur.execute("ALTER TABLE ai_picks ADD COLUMN sport TEXT")
    if "line" not in cols:
        cur.execute("ALTER TABLE ai_picks ADD COLUMN line REAL")
    conn.commit()
    conn.close()

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
# -------------------------
# AI Picks Table (Refactored)
# -------------------------


def init_ai_picks():
    """
    Ensures the ai_picks table exists and has the correct schema.
    This is the single source of truth for the table structure.
    """
    conn = get_db()
    cur = conn.cursor()

    # 1. Create the table with the ideal schema if it doesn't exist
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
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Check for any missing columns and add them (for backward compatibility)
    cur.execute("PRAGMA table_info(ai_picks)")
    existing_cols = {row['name'] for row in cur.fetchall()}

    required_cols = {
        "game": "TEXT", "sport": "TEXT", "pick": "TEXT", "market": "TEXT",
        "line": "REAL", "odds_american": "REAL", "confidence": "TEXT",
        "reasoning": "TEXT", "date": "TIMESTAMP"
    }

    for col, col_type in required_cols.items():
        if col not in existing_cols:
            print(f"⚠️ Adding missing column '{col}' to ai_picks table.")
            cur.execute(f"ALTER TABLE ai_picks ADD COLUMN {col} {col_type}")

    conn.commit()
    conn.close()


def list_ai_picks(limit=50):
    """Return most recent AI picks from the database."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ai_picks ORDER BY date DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def insert_ai_picks(picks: list):
    """Batch inserts multiple AI picks using a single transaction for efficiency."""
    conn = get_db()
    cur = conn.cursor()

    picks_to_insert = []
    for p in picks:
        # Sanitize data before insertion
        try:
            line = float(p.get("line"))
        except (TypeError, ValueError):
            line = None

        try:
            odds = float(p.get("odds_american"))
        except (TypeError, ValueError):
            odds = None

        picks_to_insert.append((
            p.get("game"), p.get("sport"), p.get("pick"), p.get("market"),
            line, odds, p.get("confidence"), p.get("reasoning")
        ))

    # Use executemany for an efficient batch insert
    cur.executemany("""
        INSERT INTO ai_picks (game, sport, pick, market, line, odds_american, confidence, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, picks_to_insert)

    conn.commit()
    conn.close()


def insert_ai_pick(pick: dict):
    """Insert a single AI pick safely."""
    conn = get_db()
    cur = conn.cursor()

    # Defensive handling for line values (avoid "ML" issues)
    line_value = pick.get("line")
    try:
        line_value = float(line_value)
    except (TypeError, ValueError):
        line_value = None

    # Defensive handling for odds (use odds_american only)
    odds_value = pick.get("odds_american")
    try:
        odds_value = float(odds_value)
    except (TypeError, ValueError):
        odds_value = None

    cur.execute("""
        INSERT INTO ai_picks (game, sport, pick, market, line, odds_american, confidence, reasoning)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pick.get("game"),
        pick.get("sport"),
        pick.get("pick"),
        pick.get("market"),
        line_value,
        odds_value,
        pick.get("confidence"),
        pick.get("reasoning"),
    ))

    conn.commit()
    conn.close()
