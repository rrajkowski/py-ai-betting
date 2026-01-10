# pages/home_page.py
"""
Public-facing home page with hero section, results, and free daily pick.
No authentication required - fully public.
"""
from app.auth import is_admin
import streamlit as st
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.db import get_db, list_ai_picks
import random

# --- Page Configuration ---
st.set_page_config(
    page_title="RAGE Sports Picks - AI vs Vegas",
    page_icon="🏆",
    layout="wide"
)

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar Navigation (Public) ---
st.sidebar.markdown("### Navigation")
st.sidebar.page_link("pages/home_page.py", label="Home", icon="🏠")
st.sidebar.page_link("pages/rage_picks_page.py",
                     label="RAGE Picks", icon="🤖")
st.sidebar.page_link("pages/live_scores_page.py",
                     label="Live Scores", icon="📊")
st.sidebar.markdown("---")

# --- Admin Section (if logged in) ---
if is_admin():
    st.sidebar.markdown("### ⚙️ Admin")
    st.sidebar.page_link("pages/admin_manual_picks.py",
                         label="Manual Picks", icon="🔧")

# --- Helper Functions ---


def get_7day_stats():
    """Calculate last 7 days performance stats using same logic as rage_picks_page."""
    conn = get_db()
    cur = conn.cursor()

    # Get picks from last 7 days
    seven_days_ago = (datetime.now(timezone.utc) -
                      timedelta(days=7)).isoformat()

    query = """
    SELECT
        SUM(CASE WHEN result = 'Win' THEN 1 ELSE 0 END) AS total_wins,
        SUM(CASE WHEN result = 'Loss' THEN 1 ELSE 0 END) AS total_losses,
        SUM(CASE WHEN result = 'Push' THEN 1 ELSE 0 END) AS total_pushes,
        SUM(
            CASE
                WHEN result = 'Win' AND odds_american > 0 THEN (odds_american / 100.0)
                WHEN result = 'Win' AND odds_american < 0 THEN (100.0 / ABS(odds_american))
                WHEN result = 'Loss' THEN -1.0
                ELSE 0
            END
        ) AS net_units
    FROM ai_picks
    WHERE date >= ? AND result IN ('Win', 'Loss', 'Push');
    """
    cur.execute(query, (seven_days_ago,))
    row = cur.fetchone()
    conn.close()

    if not row or row[0] is None:
        return {"wins": 0, "losses": 0, "pushes": 0, "units": 0.0, "win_rate": 0, "roi": 0}

    wins = row[0] or 0
    losses = row[1] or 0
    pushes = row[2] or 0
    units = round(row[3] or 0.0, 2)
    total = wins + losses + pushes
    win_rate = (wins / total * 100) if total > 0 else 0
    roi = (units / total * 100) if total > 0 else 0

    return {
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "units": units,
        "win_rate": round(win_rate, 1),
        "roi": round(roi, 1)
    }


def get_todays_free_pick():
    """Get the best pick from today (highest confidence)."""
    conn = get_db()
    cur = conn.cursor()

    today = datetime.now(timezone.utc).date().isoformat()

    cur.execute("""
        SELECT * FROM ai_picks
        WHERE date LIKE ? AND result = 'Pending'
        ORDER BY confidence DESC
        LIMIT 1
    """, (f"{today}%",))

    pick = cur.fetchone()
    conn.close()

    return dict(pick) if pick else None


def format_confidence_stars(confidence_str):
    """Convert confidence string to star rating."""
    if not confidence_str:
        return "N/A"
    try:
        stars = int(confidence_str[0])
        return "⭐" * stars
    except (ValueError, IndexError):
        return confidence_str


# --- HERO SECTION ---
st.markdown("""
<style>
    /* Global Styling */
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Hero Section */
    .hero-title {
        font-size: 3.2em;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.1em;
        background: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .hero-subtitle {
        font-size: 1.4em;
        text-align: center;
        color: #666;
        margin-bottom: 2em;
        font-weight: 500;
    }

    /* Stats */
    .stat-value {
        font-size: 2.8em;
        font-weight: 800;
        color: #1f77b4;
    }

    .stat-label {
        font-size: 0.85em;
        color: #999;
        margin-top: 0.3em;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Section Headers */
    .section-header {
        font-size: 1.8em;
        font-weight: 700;
        margin-top: 1.5em;
        margin-bottom: 0.5em;
        color: #1a1a1a;
    }

    /* Cards */
    .card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 1.5em;
        margin: 1em 0;
        border-left: 4px solid #1f77b4;
    }

    /* CTA Buttons */
    .cta-section {
        text-align: center;
        padding: 2em 0;
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #999;
        font-size: 0.9em;
        padding: 2em 0;
        border-top: 1px solid #eee;
        margin-top: 3em;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">AI vs Vegas — Public Record</div>',
            unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">No locks. No deletes. Just units.</div>',
            unsafe_allow_html=True)

# Get 7-day stats
stats = get_7day_stats()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Last 7 Days", f"+{stats['units']}u", delta=None)
with col2:
    st.metric("Win Rate", f"{stats['win_rate']}%", delta=None)
with col3:
    st.metric("ROI", f"+{stats['roi']}%", delta=None)

st.caption("✓ All picks posted before games · Full history below")

# CTA Button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("📊 View Today's Picks", use_container_width=True, type="primary"):
        st.switch_page("pages/rage_picks_page.py")

st.markdown("---")

# --- TODAY'S FREE PICK SECTION ---
st.subheader("🎁 TODAY'S FREE PICK")

free_pick = get_todays_free_pick()

if free_pick:
    sport = free_pick.get('sport', 'N/A')
    game = free_pick.get('game', 'N/A')
    pick = free_pick.get('pick', 'N/A')
    market = free_pick.get('market', 'N/A').upper()
    line = free_pick.get('line', '-')
    odds = free_pick.get('odds_american', '?')

    st.markdown(f"""
    - **🏟️ Game:** {sport} · {game}
    - **👉 Pick:** {pick} ({market})
    - **📏 Line:** {line}
    - **💵 Odds:** {odds}
    """)

    st.caption("Tail or fade. We post the result either way.")
else:
    st.info("No picks posted yet today. Check back soon!")

st.markdown("---")

# --- WHAT THIS IS SECTION ---
st.subheader("❓ WHAT THIS IS")
st.markdown("### This Is Not a Capper. It's an AI Pick Engine.")

st.markdown("""
<div style="font-size: 1.1em; line-height: 1.8;">

- 🤖 **Multiple AI models** scan spreads, totals, and props.
- 📊 **You watch the models perform** and tail the winners.

</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- HOW IT WORKS SECTION ---
st.subheader("⚙️ HOW IT WORKS")

st.markdown("""
<div style="font-size: 1.1em; line-height: 1.8;">

- **1️⃣ Models Scan** — Lines pulled across major books in real time.
- **2️⃣ Models Post** — Every pick is timestamped before kickoff.
- **3️⃣ Results Logged** — Wins. Losses. Units. Nothing gets deleted.
- **4️⃣ You Decide** — Tail, fade, parlay, or ignore.

</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- THE RECEIPTS SECTION ---
st.subheader("📜 THE RECEIPTS")
st.markdown("**Public Performance Log**")

picks = list_ai_picks(limit=20)

if picks:
    # Create display data
    display_data = []
    for p in picks:
        if p.get('result') in ['Win', 'Loss', 'Push']:
            display_data.append({
                "Date": p.get('date', 'N/A')[:10],
                "Sport": p.get('sport', 'N/A'),
                "Pick": f"{p.get('pick', 'N/A')} ({p.get('market', 'N/A').upper()})",
                "Odds": p.get('odds_american', '-'),
                "Units": "1u",
                "Result": p.get('result', 'Pending')
            })

    if display_data:
        st.dataframe(display_data, use_container_width=True, hide_index=True)
    else:
        st.info("No settled picks yet.")
else:
    st.info("No picks in history.")

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("📋 View Full History", use_container_width=True):
        st.switch_page("pages/rage_picks_page.py")

st.markdown("---")

# --- WHY USE THIS SECTION ---
st.subheader("✅ WHY USE THIS")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    - **✋ No "LOCK OF THE DAY"** — No hype, just data
    - **🚫 No Telegram pump-and-dump** — Transparent from day one
    - **📊 No edited records** — All picks stay in the database
    """)

with col2:
    st.markdown("""
    - **🤖 Multiple AI models** — Diverse perspectives, better edges
    - **📈 Transparent unit tracking** — See every win and loss
    - **🎯 Built to beat closing lines** — Not designed to sell picks
    """)

st.markdown("---")

# --- FAQ SECTION ---
st.subheader("❓ FAQ")

with st.expander("Is this gambling advice?"):
    st.markdown("No. It's data. You decide what to do with it.")

with st.expander("Do you hide losses?"):
    st.markdown("No. Losses stay. That's the point.")

with st.expander("Is this paid?"):
    st.markdown("Currently free. Advanced features coming later.")

with st.expander("What sports?"):
    st.markdown("NBA, NFL, MLB, NCAAF, NCAAB, NHL, more coming.")

st.markdown("---")

# --- FINAL CTA SECTION ---
st.markdown("""
<div style="text-align: center; padding: 3em 0; background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%); border-radius: 8px; margin: 2em 0;">
    <h2 style="margin: 0; color: #1a1a1a;">The Picks Are Public.</h2>
    <h2 style="margin: 0.5em 0 0 0; color: #1f77b4;">The Results Don't Lie.</h2>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🎯 See Today's Picks", use_container_width=True, type="primary"):
        st.switch_page("pages/rage_picks_page.py")

st.markdown("---")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9em; padding: 2em 0;">
    <p><strong>For entertainment and informational purposes only.</strong></p>
    <p>No guarantees. No financial advice. If you're mad about a loss, blame variance — not the model.</p>
</div>
""", unsafe_allow_html=True)
