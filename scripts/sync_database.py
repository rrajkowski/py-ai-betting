#!/usr/bin/env python3
"""
Sync database from Streamlit Cloud to local environment.

This script helps you download the production database from Streamlit Cloud
to your local machine without overwriting production data when you push code.

Usage:
    python scripts/sync_database.py

Requirements:
    - Streamlit Cloud app must be running
    - You must have access to the app's file system (via Streamlit's file manager)
"""

import os
import shutil
import sqlite3
from datetime import datetime

# Database paths
LOCAL_DB = "bets.db"
BACKUP_DIR = "backups"

def create_backup(db_path):
    """Create a timestamped backup of the database."""
    if not os.path.exists(db_path):
        print(f"⚠️  No database found at {db_path}")
        return None

    # Create backups directory if it doesn't exist
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # Create timestamped backup filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"bets_{timestamp}.db")

    # Copy database
    shutil.copy2(db_path, backup_path)
    print(f"✅ Backup created: {backup_path}")

    return backup_path

def get_db_stats(db_path):
    """Get statistics about the database."""
    if not os.path.exists(db_path):
        return None

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    stats = {}

    # Get ai_picks count
    cursor.execute("SELECT COUNT(*) FROM ai_picks")
    stats['ai_picks'] = cursor.fetchone()[0]

    # Get pending picks count
    cursor.execute("SELECT COUNT(*) FROM ai_picks WHERE result = 'Pending'")
    stats['pending_picks'] = cursor.fetchone()[0]

    # Get prompt_context count
    cursor.execute("SELECT COUNT(*) FROM prompt_context")
    stats['prompt_context'] = cursor.fetchone()[0]

    # Get historical_games count
    cursor.execute("SELECT COUNT(*) FROM historical_games")
    stats['historical_games'] = cursor.fetchone()[0]

    conn.close()

    return stats

def print_db_stats(label, stats):
    """Print database statistics."""
    if not stats:
        print(f"{label}: No database found")
        return

    print(f"\n{label}:")
    print(f"  Total picks:       {stats['ai_picks']}")
    print(f"  Pending picks:     {stats['pending_picks']}")
    print(f"  Context entries:   {stats['prompt_context']}")
    print(f"  Historical games:  {stats['historical_games']}")

def main():
    print("=" * 80)
    print("DATABASE SYNC TOOL - RAGE Sports Picks")
    print("=" * 80)

    # Check if local database exists
    if os.path.exists(LOCAL_DB):
        print("\n📊 Current local database stats:")
        local_stats = get_db_stats(LOCAL_DB)
        print_db_stats("Local Database", local_stats)

        # Create backup
        print("\n💾 Creating backup of local database...")
        backup_path = create_backup(LOCAL_DB)

        if backup_path:
            print(f"✅ Local database backed up to: {backup_path}")
    else:
        print(f"\n⚠️  No local database found at {LOCAL_DB}")

    print("\n" + "=" * 80)
    print("MANUAL SYNC INSTRUCTIONS")
    print("=" * 80)

    print("""
Since Streamlit Cloud doesn't provide direct database download access,
you need to manually sync the database:

OPTION 1: Use Streamlit Cloud File Manager (Recommended)
---------------------------------------------------------
1. Go to: https://share.streamlit.io/
2. Click on your app: rage-sports-picks
3. Click "Manage app" → "Settings" → "Advanced"
4. Look for "Download app files" or use the file browser
5. Download bets.db from the app's root directory
6. Replace your local bets.db with the downloaded file

OPTION 2: Add Database Export Feature to App
---------------------------------------------
Add this code to your Streamlit app (temporarily):

```python
import streamlit as st

if st.sidebar.button("📥 Download Database"):
    with open("bets.db", "rb") as f:
        st.download_button(
            label="Download bets.db",
            data=f,
            file_name=f"bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            mime="application/octet-stream"
        )
```

Then:
1. Deploy the code to Streamlit Cloud
2. Click the "Download Database" button
3. Save the file as bets.db in your local directory

OPTION 3: Use SQLite Browser (For Viewing Only)
------------------------------------------------
If you just want to view production data:
1. Install DB Browser for SQLite: https://sqlitebrowser.org/
2. Use Streamlit's file manager to view the database online
3. Or download and open locally

AFTER SYNCING:
--------------
Run this script again to see the updated stats:
    python scripts/sync_database.py
""")

    print("\n" + "=" * 80)
    print("✅ Backup complete! You can now safely sync from production.")
    print("=" * 80)

if __name__ == "__main__":
    main()

