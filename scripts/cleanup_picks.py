import os
import sqlite3
from datetime import UTC, datetime

# Define the path to your database file
DB_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "bets.db"
)
TABLE_NAME = "ai_picks"


def delete_low_confidence_picks(conn):
    """Deletes low-confidence picks (confidence < 2) but only if result = 'Pending'."""
    print("🔍 Scanning for low-confidence pending picks...")
    cur = conn.cursor()

    cur.execute(
        f"""
        DELETE FROM {TABLE_NAME}
        WHERE (confidence IS NULL OR CAST(confidence AS INTEGER) < 2)
        AND (result IS NULL OR LOWER(result) = 'pending')
        """
    )
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} low-confidence pending picks.")
    else:
        print("No low-confidence pending picks found.")


def delete_duplicate_picks(conn):
    """Deletes duplicate pending picks, keeping only the most recent per market/pick."""
    print("\n🔍 Scanning for duplicate pending picks...")
    cur = conn.cursor()

    query = f"""
        DELETE FROM {TABLE_NAME}
        WHERE (result IS NULL OR LOWER(result) = 'pending')
        AND id NOT IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY market, pick
                           ORDER BY date DESC
                       ) AS rn
                FROM {TABLE_NAME}
                WHERE (result IS NULL OR LOWER(result) = 'pending')
            ) ranked
            WHERE rn = 1
        )
    """
    cur.execute(query)
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} duplicate pending picks.")
    else:
        print("No duplicate pending picks found.")


def delete_spread_duplicates_same_team(conn):
    """
    Deletes duplicate spread picks for the same team in the same game.
    Handles cases like:
    - "Tulane Green Wave +17.5" and "Tulane Green Wave" (same team, same line)
    Keeps only the most recent pick.
    """
    print("\n🔍 Scanning for duplicate spread picks (same team, same game)...")
    cur = conn.cursor()

    # Get all pending spread picks
    cur.execute(f"""
        SELECT id, game, market, pick, line, date
        FROM {TABLE_NAME}
        WHERE (result IS NULL OR LOWER(result) = 'pending')
        AND LOWER(market) = 'spreads'
        ORDER BY game, line, date DESC
    """)

    picks = cur.fetchall()
    to_delete = []
    seen_game_team_line = {}

    import re

    for pick_id, game, _market, pick, line, _date in picks:
        if not game or not pick or line is None:
            continue

        # Normalize the pick to extract team name
        pick_normalized = pick.lower().strip()

        # Remove line value from pick string if present
        if line is not None:
            patterns = [
                rf'\s*\+?\-?{re.escape(str(line))}\s*$',
                rf'\s*\+{re.escape(str(abs(float(line))))}\s*$',
                rf'\s*\-{re.escape(str(abs(float(line))))}\s*$',
            ]
            for pattern in patterns:
                pick_normalized = re.sub(pattern, '', pick_normalized)

        # Remove any remaining +/- at the end
        pick_normalized = re.sub(r'\s*[\+\-]\s*$', '', pick_normalized).strip()

        # Create a key: (game, team_name, abs(line))
        key = (game.lower().strip(), pick_normalized, abs(float(line)))

        if key in seen_game_team_line:
            # This is a duplicate - mark for deletion
            to_delete.append(pick_id)
        else:
            # First occurrence - keep it
            seen_game_team_line[key] = pick_id

    # Delete duplicates
    if to_delete:
        placeholders = ','.join('?' * len(to_delete))
        cur.execute(f"""
            DELETE FROM {TABLE_NAME}
            WHERE id IN ({placeholders})
        """, to_delete)
        conn.commit()
        print(
            f"✅ Deleted {len(to_delete)} duplicate spread picks (same team/game/line).")
    else:
        print("No duplicate spread picks found.")


def delete_conflicting_picks(conn):
    """Deletes conflicting pending picks (same game+market, opposite sides)."""
    print("\n🔍 Scanning for conflicting pending picks...")
    cur = conn.cursor()

    query = f"""
        DELETE FROM {TABLE_NAME}
        WHERE (result IS NULL OR LOWER(result) = 'pending')
        AND id NOT IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY game, market
                           ORDER BY date DESC
                       ) AS rn
                FROM {TABLE_NAME}
                WHERE (result IS NULL OR LOWER(result) = 'pending')
            ) ranked
            WHERE rn = 1
        )
    """
    cur.execute(query)
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} conflicting pending picks.")
    else:
        print("No conflicting pending picks found.")


def delete_stuck_pending_picks(conn):
    """
    Deletes pending picks with a 'commence_time' more than 1 day in the past.
    This removes expired games that are still marked as pending.
    Completed games (Win/Loss/Push) are preserved for historical performance.
    """
    print("\n🔍 Scanning for expired pending picks (>1 day old)...")
    cur = conn.cursor()

    # Calculate cutoff time (1 day ago)
    from datetime import timedelta
    cutoff_time = datetime.now(UTC) - timedelta(days=1)
    cutoff_str = cutoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    query = f"""
        DELETE FROM {TABLE_NAME}
        WHERE
            (result IS NULL OR LOWER(result) = 'pending') AND
            (commence_time IS NOT NULL AND commence_time < '{cutoff_str}')
    """
    cur.execute(query)
    deleted_count = cur.rowcount
    conn.commit()

    if deleted_count > 0:
        print(f"✅ Deleted {deleted_count} expired pending picks (>1 day old).")
    else:
        print("No expired pending picks found.")


def delete_rows_without_date(conn):
    """Deletes PENDING picks from the ai_picks table where the date is NULL."""
    print("\n🔍 Scanning for pending picks with no date...")

    try:
        cur = conn.cursor()

        # SQL query to delete rows where the 'date' column is NULL AND result is pending
        # This preserves completed games (Win/Loss/Push) even if they have NULL dates
        query = f"""
            DELETE FROM {TABLE_NAME}
            WHERE date IS NULL
            AND (result IS NULL OR LOWER(result) = 'pending')
        """

        cur.execute(query)

        # Get the number of rows that were deleted
        deleted_count = cur.rowcount

        # Commit the changes to the database
        conn.commit()

        if deleted_count > 0:
            print(
                f"✅ Deleted {deleted_count} pending picks that were missing a date.")
        else:
            print("No pending picks with missing dates found.")

    except Exception as e:
        print(f"❌ An error occurred during the cleanup: {e}")
        conn.rollback()  # Roll back any changes if an error occurs


def main():
    """
    Runs cleanup tasks for pending picks only.

    This will NOT delete completed games (Win/Loss/Push).
    Only removes:
    - Low confidence pending picks (< 2 stars)
    - Duplicate pending picks (same market/pick)
    - Duplicate spread picks (same team/game/line with different formatting)
    - Conflicting pending picks (same game/market, opposite sides)
    - Expired pending picks (>1 day old with no result)
    - Picks with missing dates
    """
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at '{DB_PATH}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Connected to database: {DB_PATH}\n")
        print("🧹 Cleanup will ONLY affect PENDING picks, not completed games.\n")

        delete_low_confidence_picks(conn)
        delete_duplicate_picks(conn)
        # NEW: Clean up spread duplicates
        delete_spread_duplicates_same_team(conn)
        delete_conflicting_picks(conn)
        delete_stuck_pending_picks(conn)
        delete_rows_without_date(conn)

        print("\n✅ Database cleanup complete!")
        print("📊 All completed games (Win/Loss/Push) remain intact.")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
