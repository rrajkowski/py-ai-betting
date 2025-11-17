import sqlite3
import os
from datetime import datetime, timezone


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
    Deletes pending picks with a 'commence_time' more than 7 days in the past.
    This targets truly stuck picks while allowing time for scores to be updated.
    """
    print("\n🔍 Scanning for stuck pending picks (>7 days old)...")
    cur = conn.cursor()

    # Calculate cutoff time (7 days ago)
    from datetime import timedelta
    cutoff_time = datetime.now(timezone.utc) - timedelta(days=7)
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
        print(f"✅ Deleted {deleted_count} stuck pending picks (>7 days old).")
    else:
        print("No stuck pending picks found.")


def delete_rows_without_date(conn):
    """Deletes all rows from the ai_picks table where the date is NULL."""
    print("🧹 Starting cleanup of picks with no date...")

    try:
        cur = conn.cursor()

        # SQL query to delete rows where the 'date' column is NULL
        query = f"DELETE FROM {TABLE_NAME} WHERE date IS NULL"

        cur.execute(query)

        # Get the number of rows that were deleted
        deleted_count = cur.rowcount

        # Commit the changes to the database
        conn.commit()

        if deleted_count > 0:
            print(
                f"✅ Success! Deleted {deleted_count} picks that were missing a date.")
        else:
            print(
                "👍 No picks with missing dates were found. Your database is already clean!")

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
    - Conflicting pending picks (same game/market, opposite sides)
    - Stuck pending picks (>7 days old with no result)
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
