import sqlite3
import os
import json
from typing import Optional

# NOTE: Assumes bets.db lives in the root directory (two levels up from /app/utils/)
DB_PATH = os.getenv(
    "SQLITE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "bets.db")
)
CONTEXT_TABLE = "prompt_context"


def get_db():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_prompt_context_db():
    """
    Creates the unified prompt_context table if it does not exist.
    """
    conn = get_db()
    cur = conn.cursor()

    # 1. Database Setup: Create the unified prompt_context table
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {CONTEXT_TABLE} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,        -- "storage" or "realtime"
            context_type TEXT NOT NULL,    -- e.g. "expert_consensus", "public_consensus"
            game_id TEXT NOT NULL,         -- e.g. "NFL2025-WK5-KCvsBUF"
            match_date TEXT NOT NULL,      -- YYYY-MM-DD
            sport TEXT,                    -- NEW: Added sport filter column (e.g., 'NFL')
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
    conn.close()
    print(f"✅ Unified context database '{CONTEXT_TABLE}' initialized.")


def init_ai_picks():
    """
    Initializes the ai_picks table with an improved schema,
    including a new 'commence_time' column for accurate pending pick cleanup.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_picks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            sport TEXT,
            game TEXT,
            pick TEXT,
            market TEXT,
            line REAL,
            odds_american INTEGER,
            result TEXT DEFAULT 'Pending',
            confidence TEXT,
            reasoning TEXT,
            commence_time TEXT
        )
    """)

    # --- Schema migration: Add 'commence_time' column if missing ---
    cur.execute("PRAGMA table_info(ai_picks)")
    cols = {row['name'] for row in cur.fetchall()}
    if 'commence_time' not in cols:
        cur.execute("ALTER TABLE ai_picks ADD COLUMN commence_time TEXT")

    conn.commit()
    conn.close()


def insert_ai_picks(picks):
    """
    Batch inserts AI-generated picks into the database.
    """
    conn = get_db()
    cur = conn.cursor()

    for pick in picks:
        try:
            cur.execute("""
                INSERT INTO ai_picks (date, sport, game, pick, market, line, odds_american, result, confidence, reasoning, commence_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pick.get("commence_time"),  # Use commence_time for the date field
                pick.get("sport"),
                pick.get("game"),
                pick.get("pick"),
                pick.get("market"),
                pick.get("line"),
                pick.get("odds_american"),
                pick.get("result", "Pending"),
                pick.get("confidence"),
                pick.get("reasoning"),
                pick.get("commence_time")
            ))
        except Exception as e:
            print(f"❌ Error inserting AI pick: {e}")

    conn.commit()
    conn.close()


def insert_context(category: str, context_type: str, game_id: str, match_date: str, sport: str, data: dict, source: str, team_pick: Optional[str] = None):
    """
    Inserts a single row of context data into the prompt_context table.
    Data object is serialized to JSON string before insertion.
    """
    conn = get_db()
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
    conn.close()


def fetch_context_by_date(match_date: str, sport: str):
    """
    Fetches all context records for a specific date AND sport.
    Returns a list of dictionaries with 'data' decoded from JSON.
    Includes debug logging to help diagnose context issues.
    """
    conn = get_db()
    cur = conn.cursor()

    # Debug: Check what sports are in the database
    cur.execute(f"SELECT DISTINCT sport FROM {CONTEXT_TABLE}")
    available_sports = [row[0] for row in cur.fetchall()]
    print(f"🔍 DB Debug: Available sports in database: {available_sports}")

    # Debug: Check what dates are in the database for this sport
    cur.execute(
        f"SELECT DISTINCT match_date FROM {CONTEXT_TABLE} WHERE sport = ?", (sport,))
    available_dates = [row[0] for row in cur.fetchall()]
    # Show first 5
    print(f"🔍 DB Debug: Available dates for {sport}: {available_dates[:5]}...")

    # Main query
    cur.execute(f"""
        SELECT * FROM {CONTEXT_TABLE} WHERE match_date = ? AND sport = ?
    """, (match_date, sport,))

    rows = [dict(r) for r in cur.fetchall()]

    # Debug: Show breakdown by context_type
    if rows:
        context_types = {}
        for row in rows:
            ct = row.get('context_type', 'unknown')
            context_types[ct] = context_types.get(ct, 0) + 1
        print(f"🔍 DB Debug: Context types found: {context_types}")
    else:
        print(
            f"⚠️ DB Debug: No records found for sport='{sport}' and date='{match_date}'")

    conn.close()

    for row in rows:
        try:
            row['data'] = json.loads(row['data'])
        except (TypeError, json.JSONDecodeError):
            row['data'] = {}

    return rows
