# app/utils/admin_sidebar.py
"""
Shared admin sidebar utilities for admin-only features.
Provides consistent admin controls across pages.
"""
import logging
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime

import streamlit as st

from app.auth import is_admin
from app.db import DB_PATH, backup_db

logger = logging.getLogger(__name__)


def render_refresh_daily_pick_button(generate_pick_callback, insert_pick_callback):
    """
    Render the "Refresh Daily Pick" button for the home page.

    Args:
        generate_pick_callback: Function to generate a random daily pick
        insert_pick_callback: Function to insert the pick into database
    """
    if not is_admin():
        return

    if st.sidebar.button("🔄 Refresh Daily Pick", type="secondary"):
        logger.info("[Refresh Daily Pick Button] Clicked!")

        pick_data = generate_pick_callback()

        if pick_data:
            logger.info(
                f"[insert_ai_pick] Inserting pick: {pick_data.get('game')}")
            inserted = insert_pick_callback(pick_data)
            if inserted:
                logger.info("[insert_ai_pick] Pick inserted successfully")
                st.sidebar.success("✅ Daily pick refreshed!")
                st.rerun()
            else:
                logger.warning(
                    "[insert_ai_pick] Pick already exists in database")
                st.sidebar.warning("⚠️ This pick is already in the database!")
        else:
            logger.error("[Refresh Daily Pick] No pick data returned")
            st.sidebar.error("❌ Could not generate pick. No games available.")


def render_maintenance_section(update_results_callback):
    """
    Render the maintenance section with update and cleanup buttons.

    Args:
        update_results_callback: Function to update pick results
    """
    if not is_admin():
        return

    st.sidebar.markdown("### ⚙️ Maintenance")

    if st.sidebar.button("🔁 Update Pick Results"):
        update_results_callback()
        st.success("RAGE Sports Picks updated from live scores!")

    if st.sidebar.button("🧹 Clean Up Picks"):
        with st.spinner("Cleaning up database..."):
            import io
            import sys

            from scripts.cleanup_picks import main as cleanup_main

            # Capture output from cleanup script
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            try:
                cleanup_main()
                output = buffer.getvalue()
                sys.stdout = old_stdout

                # Show output in success message
                st.success("Database cleanup complete!")
                with st.expander("📋 Cleanup Details"):
                    st.code(output)
            except Exception as e:
                sys.stdout = old_stdout
                st.error(f"Cleanup failed: {e}")


def render_backup_restore_section():
    """
    Render the backup and restore section with download and upload functionality.
    """
    if not is_admin():
        return

    # st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Backup & Restore")

    # Manual server-side backup button
    if st.sidebar.button("🗄️ Create Server Backup"):
        path = backup_db(tag="manual")
        if path:
            st.sidebar.success(
                f"✅ Server backup created: {os.path.basename(path)}")
        else:
            st.sidebar.error("❌ Backup failed — check logs.")

    # Download backup button
    if st.sidebar.button("⬇️ Download Backup"):
        if os.path.exists(DB_PATH):
            with open(DB_PATH, "rb") as f:
                db_bytes = f.read()

            # Get current timestamp for filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bets_backup_{timestamp}.db"

            st.sidebar.download_button(
                label="📥 Click to Download",
                data=db_bytes,
                file_name=filename,
                mime="application/octet-stream",
                key="download_backup"
            )
            st.sidebar.success(f"✅ Backup ready: {filename}")
        else:
            st.sidebar.error("❌ Database file not found!")

    # Upload/restore backup button
    uploaded_file = st.sidebar.file_uploader(
        "⬆️ Merge Backup (Smart Restore)",
        type=["db"],
        key="upload_backup",
        help="Upload a backup to merge with current data. Only adds new picks and updates results - no duplicates!"
    )

    if uploaded_file is not None and st.sidebar.button("🔄 Merge Backup Data", type="primary"):
        _merge_backup_data(uploaded_file)


def _merge_backup_data(uploaded_file):
    """
    Merge backup database with current database.
    Only adds new picks and updates results - no duplicates.
    Works on both local development (./bets.db) and Railway (/app/data/bets.db).
    """
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        backup_db_path = tmp_file.name

    # Use the correct database path (Railway or local)
    current_db = DB_PATH

    # Create safety backup of current database
    if os.path.exists(current_db):
        # Determine backup directory based on environment
        if os.getenv("RAILWAY_ENVIRONMENT"):
            # Railway: use /app/data/backups
            backup_dir = "/app/data/backups"
        else:
            # Local: use ./backups
            backup_dir = "backups"

        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_backup = f"{backup_dir}/bets_before_merge_{timestamp}.db"
        shutil.copy2(current_db, safety_backup)
        st.sidebar.info(f"📦 Safety backup: {safety_backup}")

    # Merge logic: Add new picks and update results
    try:
        # Connect to both databases
        current_conn = sqlite3.connect(current_db)
        current_conn.row_factory = sqlite3.Row
        backup_conn = sqlite3.connect(backup_db_path)
        backup_conn.row_factory = sqlite3.Row

        current_cur = current_conn.cursor()
        backup_cur = backup_conn.cursor()

        # Get all picks from backup
        backup_cur.execute("SELECT * FROM ai_picks")
        backup_picks = backup_cur.fetchall()

        added = 0
        updated = 0
        skipped = 0

        for pick in backup_picks:
            # Check if pick exists (match by game, pick, market, line, date)
            current_cur.execute("""
                SELECT id, result FROM ai_picks
                WHERE game = ? AND pick = ? AND market = ?
                AND COALESCE(line, 0) = COALESCE(?, 0)
                AND date(commence_time) = date(?)
            """, (pick['game'], pick['pick'], pick['market'], pick['line'], pick['commence_time']))

            existing = current_cur.fetchone()

            if existing:
                # Pick exists - update result if it's different (allows overriding any result)
                if existing['result'].lower() != pick['result'].lower():
                    current_cur.execute("""
                        UPDATE ai_picks SET result = ? WHERE id = ?
                    """, (pick['result'], existing['id']))
                    updated += 1
                else:
                    skipped += 1
            else:
                # New pick - insert it
                current_cur.execute("""
                    INSERT INTO ai_picks
                    (sport, game, pick, market, line, odds_american,
                     result, confidence, reasoning, date, commence_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pick['sport'], pick['game'], pick['pick'], pick['market'],
                    pick['line'], pick['odds_american'], pick['result'],
                    pick['confidence'], pick['reasoning'], pick['date'], pick['commence_time']
                ))
                added += 1

        current_conn.commit()
        current_conn.close()
        backup_conn.close()

        # Clean up temp file
        os.unlink(backup_db_path)

        # Show results
        st.sidebar.success("✅ Merge complete!")
        st.sidebar.info(
            f"📊 Added: {added} | Updated: {updated} | Skipped: {skipped}")
        st.sidebar.info(
            "🔄 Please refresh the page to see updated data.")

    except Exception as e:
        st.sidebar.error(f"❌ Merge failed: {e}")
        # Clean up temp file on error
        if os.path.exists(backup_db_path):
            os.unlink(backup_db_path)
