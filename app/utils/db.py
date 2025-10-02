import sqlite3
import os
import json

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

    # Attempt to add the 'sport' column if it was previously missing (migration)
    try:
        cur.execute(f"ALTER TABLE {CONTEXT_TABLE} ADD COLUMN sport TEXT")
        print(f"✅ Added missing 'sport' column to {CONTEXT_TABLE}")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def insert_context(category, context_type, game_id, match_date, data, sport, team_pick=None, source=None):
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
        sport,  # Now included in the insertion list
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
    """
    conn = get_db()
    cur = conn.cursor()

    # CRITICAL FIX: Added 'AND sport = ?' to the WHERE clause
    cur.execute(f"""
        SELECT * FROM {CONTEXT_TABLE} WHERE match_date = ? AND sport = ?
    """, (match_date, sport,))

    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # Decode the JSON string back into a Python object
    for row in rows:
        try:
            # The 'data' column stores the complex JSON payload
            row['data'] = json.loads(row['data'])
        except (TypeError, json.JSONDecodeError):
            row['data'] = {}
        # The 'sport' is explicitly returned, ensuring it's available for filtering
        # in the context builder.

    return rows
