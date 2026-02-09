"""
Code snippet to add to streamlit_app.py for database download feature.

Add this to the sidebar in streamlit_app.py (only for admin users):
"""

SIDEBAR_CODE = '''
# Add to streamlit_app.py sidebar (after login check)

# Database download feature (admin only)
if st.session_state.get("is_logged_in") and st.session_state.get("user_email") in ["your-admin-email@gmail.com"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔧 Admin Tools")

    if st.sidebar.button("📥 Download Database", help="Download production database"):
        import os
        from datetime import datetime

        db_path = "bets.db"
        if os.path.exists(db_path):
            with open(db_path, "rb") as f:
                db_data = f.read()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"bets_production_{timestamp}.db"

            st.sidebar.download_button(
                label="⬇️ Download bets.db",
                data=db_data,
                file_name=filename,
                mime="application/octet-stream",
                help="Download the production database"
            )

            # Show database stats
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM ai_picks")
            total_picks = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM ai_picks WHERE result = 'Pending'")
            pending_picks = cursor.fetchone()[0]

            conn.close()

            st.sidebar.info(f"""
            **Database Stats:**
            - Total picks: {total_picks}
            - Pending picks: {pending_picks}
            """)
        else:
            st.sidebar.error("Database not found!")
'''

print("=" * 80)
print("DATABASE DOWNLOAD FEATURE - Code Snippet")
print("=" * 80)
print("\nAdd this code to streamlit_app.py to enable database downloads:\n")
print(SIDEBAR_CODE)
print("\n" + "=" * 80)
print("INSTRUCTIONS:")
print("=" * 80)
print("""
1. Copy the code above
2. Open streamlit_app.py
3. Find the sidebar section (after login check)
4. Paste the code
5. Replace "your-admin-email@gmail.com" with your actual email
6. Commit and push to deploy
7. Visit the app and click "Download Database" in the sidebar
8. Save the downloaded file as bets.db in your local directory

This allows you to download the production database without SSH access!
""")
