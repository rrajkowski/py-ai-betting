import sqlite3
import os

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


def main():
    """Runs all cleanup tasks for pending picks."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: Database file not found at '{DB_PATH}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        print(f"Connected to database: {DB_PATH}\n")

        delete_low_confidence_picks(conn)
        delete_duplicate_picks(conn)
        delete_conflicting_picks(conn)

        print("\n🧹 Database cleanup complete (pending picks only)!")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
