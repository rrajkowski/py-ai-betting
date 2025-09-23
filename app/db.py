import sqlite3
import os

# Default to a file in /tmp (safe for Streamlit Cloud ephemeral FS)
DB_PATH = os.getenv("SQLITE_DB_PATH", "/tmp/bets.db")


def get_db():
    """Open a new database connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create bets table if not exists."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT NOT NULL,
            opponent TEXT NOT NULL,
            market TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def insert_bet(team: str, opponent: str, market: str):
    """Insert a new bet."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO bets (team, opponent, market) VALUES (?, ?, ?)",
        (team, opponent, market),
    )
    conn.commit()
    conn.close()


def list_bets():
    """Fetch all bets ordered by newest first."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM bets ORDER BY date DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
