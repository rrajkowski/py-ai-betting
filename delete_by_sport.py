# delete_by_sport.py

import sqlite3
import os

# --- Configuration ---
DB_PATH = "bets.db"
# Set the exact sport key you want to delete
SPORT_TO_DELETE = 'americanfootball_nfl'


def delete_picks_by_sport(sport_key: str):
    """
    Deletes all AI picks from the database that match a specific sport key.
    Includes a confirmation step for safety.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at '{DB_PATH}'")
        return

    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        # 1. Safety Check: Count the rows first
        cur.execute(
            "SELECT COUNT(*) FROM ai_picks WHERE sport = ?", (sport_key,))
        count = cur.fetchone()[0]

        if count == 0:
            print(
                f"No picks found with sport key '{sport_key}'. Nothing to delete.")
            return

        # 2. Ask for user confirmation
        print(f"Found {count} picks with sport key '{sport_key}'.")
        confirm = input(
            "Are you sure you want to permanently delete these rows? (y/n): ")

        if confirm.lower() != 'y':
            print("Deletion cancelled by user.")
            return

        # 3. Execute the DELETE statement
        cur.execute("DELETE FROM ai_picks WHERE sport = ?", (sport_key,))
        deleted_count = cur.rowcount
        conn.commit()

        print(f"✅ Success! Deleted {deleted_count} rows.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print(f"--- Preparing to delete picks for sport: {SPORT_TO_DELETE} ---")
    delete_picks_by_sport(SPORT_TO_DELETE)
