# pages/home_page.py
"""
Public-facing home page with hero section, results, and free daily pick.
No authentication required - fully public.
"""
from app.utils.sidebar import render_sidebar_navigation, render_admin_section
from app.utils.admin_sidebar import render_refresh_daily_pick_button
import streamlit as st
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.db import get_db, list_ai_picks, insert_ai_pick

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

# --- Helper Functions (defined before sidebar) ---


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
    """Get the best pick from upcoming games (highest confidence)."""
    conn = get_db()
    cur = conn.cursor()

    now_utc = datetime.now(timezone.utc)
    today = now_utc.date().isoformat()

    print(f"\n🔍 [get_todays_free_pick] Looking for pending picks...")
    print(f"   Current time: {now_utc.isoformat()}")

    # Look for pending picks with games starting in the future (next 7 days)
    # Order by confidence (highest first), then by commence_time (soonest first)
    cur.execute("""
        SELECT * FROM ai_picks
        WHERE result = 'Pending'
        AND commence_time IS NOT NULL
        AND datetime(commence_time) > datetime('now')
        ORDER BY confidence DESC, commence_time ASC
        LIMIT 1
    """)

    pick = cur.fetchone()

    if pick:
        pick_dict = dict(pick)
        print(
            f"   ✅ Found pick: {pick_dict.get('game')} - {pick_dict.get('pick')}")
        print(f"      Confidence: {pick_dict.get('confidence')}")
        print(f"      Game starts: {pick_dict.get('commence_time')}")
    else:
        print(f"   ❌ No pending picks found!")
        # Debug: show all pending picks
        cur.execute(
            "SELECT id, date, game, pick, result, commence_time FROM ai_picks WHERE result = 'Pending' ORDER BY commence_time DESC LIMIT 5")
        all_pending = cur.fetchall()
        if all_pending:
            print(f"   📋 Recent pending picks:")
            for row in all_pending:
                print(
                    f"      - {row[1]}: {row[2]} ({row[3]}) - starts: {row[5]}")
        else:
            print(f"   📋 No pending picks in database at all!")

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


def generate_random_daily_pick():
    """Generate a random daily pick from existing pending picks with stars."""
    print("\n" + "="*80)
    print("🎲 [generate_random_daily_pick] Starting...")

    conn = get_db()
    cur = conn.cursor()

    # First, check how many pending picks exist
    cur.execute("SELECT COUNT(*) FROM ai_picks WHERE result = 'Pending'")
    total_pending = cur.fetchone()[0]
    print(f"   📊 Total pending picks in database: {total_pending}")

    # Get all pending picks that have a star rating (confidence)
    cur.execute("""
        SELECT * FROM ai_picks
        WHERE result = 'Pending'
        AND confidence IS NOT NULL
        AND confidence != ''
        ORDER BY RANDOM()
        LIMIT 1
    """)

    pick = cur.fetchone()

    if pick:
        pick_dict = dict(pick)
        print(
            f"   ✅ Selected pick: {pick_dict.get('game')} - {pick_dict.get('pick')}")
        print(f"      Sport: {pick_dict.get('sport')}")
        print(f"      Market: {pick_dict.get('market')}")
        print(f"      Confidence: {pick_dict.get('confidence')}")
        print(f"      Date: {pick_dict.get('date')}")
        print(f"      Commence Time: {pick_dict.get('commence_time')}")
        conn.close()
        print("="*80 + "\n")
        return pick_dict
    else:
        print(f"   ❌ No pending picks with confidence found!")
        # Debug: show what we have
        cur.execute("""
            SELECT id, game, pick, confidence, result
            FROM ai_picks
            WHERE result = 'Pending'
            LIMIT 5
        """)
        debug_picks = cur.fetchall()
        if debug_picks:
            print(f"   📋 Sample pending picks (checking confidence field):")
            for row in debug_picks:
                print(
                    f"      - {row[1]} ({row[2]}) - confidence: '{row[3]}' - result: {row[4]}")
        else:
            print(f"   📋 No pending picks at all!")

    conn.close()
    print("="*80 + "\n")
    return None


# --- Sidebar Navigation ---
render_sidebar_navigation()

# --- Admin Section (if logged in) ---
render_admin_section()

# --- Admin Utilities ---
render_refresh_daily_pick_button(generate_random_daily_pick, insert_ai_pick)

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

st.markdown('<div style="text-align: left;"><div class="hero-title">AI vs Vegas — Public Record</div></div>',
            unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">No locks. No deletes. Just units.</div>',
            unsafe_allow_html=True)

# Get 7-day stats
stats = get_7day_stats()

st.markdown(f"""
<div style="border: 2px solid #ddd; border-radius: 12px; padding: 2em; margin: 1.5em 0;">
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 2em; text-align: center;">
        <div>
            <div style="font-size: 0.9em; color: #666; margin-bottom: 0.5em;">Last 7 Days</div>
            <div style="font-size: 2.2em; font-weight: bold; color: #1f77b4;">+{stats['units']}u</div>
        </div>
        <div>
            <div style="font-size: 0.9em; color: #666; margin-bottom: 0.5em;">Win Rate</div>
            <div style="font-size: 2.2em; font-weight: bold; color: #1f77b4;">{stats['win_rate']}%</div>
        </div>
        <div>
            <div style="font-size: 0.9em; color: #666; margin-bottom: 0.5em;">ROI</div>
            <div style="font-size: 2.2em; font-weight: bold; color: #1f77b4;">+{stats['roi']}%</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("✓ All picks posted before games · Full history below")

# CTA Button - Centered
col1, col2, col3 = st.columns([1, 0.5, 1])
with col2:
    if st.button("📊 View Today's Full Slate", type="primary", width="stretch"):
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

st.markdown("""
<div style="font-size: 1.1em; line-height: 1.8;">

**This is Not a Capper. It's an AI Pick Engine.**

🤖 **Multiple AI models** scan spreads, totals, and props.

📊 **You watch the models perform** and tail the winners.

</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- HOW IT WORKS SECTION ---
st.subheader("⚙️ HOW IT WORKS")

st.markdown("""
<div style="font-size: 1.1em; line-height: 1.8;">

**1️⃣ Models Scan** — Lines pulled across major books in real time.

**2️⃣ Models Post** — Every pick is timestamped before kickoff.

**3️⃣ Results Logged** — Wins. Losses. Units. Nothing gets deleted.

**4️⃣ You Decide** — Tail, fade, parlay, or ignore.

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
        st.dataframe(display_data, width="stretch", hide_index=True)
    else:
        st.info("No settled picks yet.")
else:
    st.info("No picks in history.")

col1, col2, col3 = st.columns([1, 0.5, 1])
with col2:
    if st.button("📋 View Full History", type="primary", width="stretch"):
        st.switch_page("pages/rage_picks_page.py")

st.markdown("---")

# --- WHY USE THIS SECTION ---
st.subheader("✅ WHY USE THIS")

st.markdown("""
- **✋ No "LOCK OF THE DAY"** — No hype, just data
- **🚫 No Telegram pump-and-dump** — Transparent from day one
- **📊 No edited records** — All picks stay in the database
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

col1, col2, col3 = st.columns([1, 0.5, 1])
with col2:
    if st.button("🎯 View Today's Full Slate", type="primary", width="stretch"):
        st.switch_page("pages/rage_picks_page.py")

st.markdown("---")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9em; padding: 2em 0;">
    <p><strong>For entertainment and informational purposes only.</strong></p>
    <p>No guarantees. No financial advice. If you're mad about a loss, blame variance — not the model.</p>
    <p>RAGE Picks &copy; 2025</p>
</div>
""", unsafe_allow_html=True)
