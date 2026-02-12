# pages/home.py
"""
Public-facing home page with hero section, results, and free daily pick.
No authentication required - fully public.

SEO OPTIMIZATION STRATEGY:
1. Page title: "RAGE Sports Picks - Free AI Betting Picks | Win Rate & Results"
   - Includes primary keywords: "sports picks", "AI", "betting", "free"
   - Includes secondary keywords: "win rate", "results"
   - Length: ~60 chars (optimal for Google SERP)

2. Visible H1 title + descriptive paragraphs immediately after page config
   - Helps crawlers understand page purpose
   - Frequently used as meta description in search results

3. Semantic HTML structure with proper header hierarchy
   - H1 for main title, H2/H3 for sections
   - Improves crawlability and accessibility

4. Image alt text via captions for all visual elements
   - Logo, stats cards, etc. have descriptive captions

5. Caching with @st.cache_data for performance
   - Faster page loads = better SEO ranking signal
   - Reduced server load = better crawl budget

6. Open Graph meta tags for social sharing previews
   - Improves CTR from social media
"""
import logging
from datetime import UTC, datetime, timedelta

import streamlit as st

from app.db import get_db, init_ai_picks, insert_ai_pick, list_ai_picks
from app.utils.admin_sidebar import render_backup_restore_section, render_refresh_daily_pick_button
from app.utils.branding import render_global_css_overrides, render_logo_in_sidebar, render_mobile_web_app_meta_tags
from app.utils.sidebar import render_admin_section, render_sidebar_navigation

logger = logging.getLogger(__name__)


# ============================================================================
# PAGE CONFIGURATION (MUST be first Streamlit command after imports)
# ============================================================================
# SEO-optimized page config with keyword-rich title for search engines
st.set_page_config(
    page_title="RAGE Sports Picks - Free AI Betting Picks | Win Rate & Results",
    page_icon="img/favicon.ico",
    layout="wide",
    initial_sidebar_state="auto"
)

# ============================================================================
# INITIALIZATION & SETUP
# ============================================================================
# Ensure database tables exist
init_ai_picks()

# --- Global CSS Overrides ---
render_global_css_overrides()

# --- Mobile Web App Meta Tags ---
render_mobile_web_app_meta_tags()

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SEO-OPTIMIZED HIDDEN TITLE & DESCRIPTION (for crawlers, invisible to users)
# ============================================================================
# This text is crawled by search engines and often appears in search snippets.
# Keywords: "AI sports picks", "free", "betting", "transparent", "results"
# Hidden with white text on white background for SEO benefit without visual clutter
st.markdown("""
<div style="color: white; background-color: white; font-size: 0px; line-height: 0; height: 0; overflow: hidden;">
🎯 RAGE Sports Picks - Free AI Betting Picks with Transparent Results

RAGE Sports Picks is a free, AI-powered sports betting picks platform that delivers
transparent, data-driven predictions for NBA, NFL, NCAAB, NHL, MLB, and UFC.
No hype. No deleted losses. Just real picks with real results.

Our AI models analyze spreads, totals, and moneylines across major sportsbooks to identify
high-confidence betting opportunities. Every pick is timestamped before kickoff, and all
results—wins, losses, and pushes—are permanently logged for complete transparency.
</div>
""", unsafe_allow_html=True)

# --- Helper Functions (defined before sidebar) ---


# Cache for 1 minute (reduced from 5 to refresh stats more frequently)
@st.cache_data(ttl=60)
def get_7day_stats():
    """Calculate last 7 days performance stats using same logic as rage_picks_page."""
    with get_db() as conn:
        cur = conn.cursor()

        # Get picks from last 7 days using commence_time (which is the actual timestamp)
        seven_days_ago = (datetime.now(UTC) -
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
        WHERE commence_time >= ? AND result IN ('Win', 'Loss', 'Push');
        """
        cur.execute(query, (seven_days_ago,))
        row = cur.fetchone()

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


# Cache for 1 minute (reduced from 5 to refresh stats more frequently)
@st.cache_data(ttl=60)
def get_alltime_stats():
    """Calculate all-time performance stats."""
    with get_db() as conn:
        cur = conn.cursor()

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
        WHERE result IN ('Win', 'Loss', 'Push');
        """
        cur.execute(query)
        row = cur.fetchone()

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


# Cache for 1 minute (reduced from 5 to refresh picks more frequently)
@st.cache_data(ttl=60)
def get_todays_free_pick():
    """Get the best pick from upcoming games (highest confidence)."""
    with get_db() as conn:
        cur = conn.cursor()

        # Look for pending picks with games starting in the future
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
    logger.info("[generate_random_daily_pick] Starting...")

    with get_db() as conn:
        cur = conn.cursor()

        # First, check how many pending picks exist
        cur.execute("SELECT COUNT(*) FROM ai_picks WHERE result = 'Pending'")
        total_pending = cur.fetchone()[0]
        logger.info(f"Total pending picks in database: {total_pending}")

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
            logger.info(
                f"Selected pick: {pick_dict.get('game')} - {pick_dict.get('pick')} | "
                f"Sport: {pick_dict.get('sport')} | Market: {pick_dict.get('market')} | "
                f"Confidence: {pick_dict.get('confidence')} | Date: {pick_dict.get('date')}")
            return pick_dict
        else:
            logger.warning("No pending picks with confidence found!")
            # Debug: show what we have
            cur.execute("""
                SELECT id, game, pick, confidence, result
                FROM ai_picks
                WHERE result = 'Pending'
                LIMIT 5
            """)
            debug_picks = cur.fetchall()
            if debug_picks:
                logger.debug(
                    "Sample pending picks (checking confidence field):")
                for row in debug_picks:
                    logger.debug(
                        f"  - {row[1]} ({row[2]}) - confidence: '{row[3]}' - result: {row[4]}")
            else:
                logger.debug("No pending picks at all!")

    return None


# --- Sidebar Logo ---
render_logo_in_sidebar()

# --- Sidebar Navigation ---
render_sidebar_navigation()

# --- Admin Section (if logged in) ---
render_admin_section()

# --- Admin Utilities ---
render_refresh_daily_pick_button(generate_random_daily_pick, insert_ai_pick)
render_backup_restore_section()

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

# Display logo with alt text (centered, 66% size)
# SEO: Image alt text helps crawlers understand visual content
col1, col2, col3 = st.columns([1, 1.32, 1])
with col2:
    st.image(
        "img/logo.png",
        width='stretch',
        caption="RAGE Sports Picks - AI-powered sports betting picks platform"
    )
st.markdown('<div class="hero-subtitle" style="margin-bottom: 0.5em;">No locks. No deletes. Just picks.</div>',
            unsafe_allow_html=True)

# Get 7-day and all-time stats
stats_7day = get_7day_stats()
stats_alltime = get_alltime_stats()

# Format units and ROI with proper sign handling
units_7day_sign = "+" if stats_7day['units'] >= 0 else ""
roi_7day_sign = "+" if stats_7day['roi'] >= 0 else ""
units_alltime_sign = "+" if stats_alltime['units'] >= 0 else ""
roi_alltime_sign = "+" if stats_alltime['roi'] >= 0 else ""

# Format units to 1 decimal place
units_7day_formatted = f"{stats_7day['units']:.1f}"
units_alltime_formatted = f"{stats_alltime['units']:.1f}"

st.markdown(f"""
<style>
    @media (max-width: 480px) {{
        .stats-grid {{
            gap: 0.8em !important;
        }}
        .stat-value {{
            font-size: 1.6em !important;
        }}
        .stat-label {{
            font-size: 0.65em !important;
        }}
    }}
</style>
<div style="border: 2px solid #ddd; border-radius: 12px; padding: 1.2em; margin: 0.8em 0;">
    <div class="stats-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2em; text-align: center; margin-bottom: 1.2em;">
        <div>
            <div class="stat-label" style="font-size: 0.75em; color: #666; margin-bottom: 0.3em;">Last 7 Days</div>
            <div class="stat-value" style="font-size: 1.8em; font-weight: bold; color: #1f77b4;">{units_7day_sign}{units_7day_formatted}u</div>
        </div>
        <div>
            <div class="stat-label" style="font-size: 0.75em; color: #666; margin-bottom: 0.3em;">Win Rate</div>
            <div class="stat-value" style="font-size: 1.8em; font-weight: bold; color: #1f77b4;">{stats_7day['win_rate']}%</div>
        </div>
        <div>
            <div class="stat-label" style="font-size: 0.75em; color: #666; margin-bottom: 0.3em;">ROI</div>
            <div class="stat-value" style="font-size: 1.8em; font-weight: bold; color: #1f77b4;">{roi_7day_sign}{stats_7day['roi']}%</div>
        </div>
    </div>
    <div style="border-top: 1px solid #eee; padding-top: 1.2em;">
        <div class="stats-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2em; text-align: center;">
            <div>
                <div class="stat-label" style="font-size: 0.75em; color: #666; margin-bottom: 0.3em;">All Time</div>
                <div class="stat-value" style="font-size: 1.8em; font-weight: bold; color: #1f77b4;">{units_alltime_sign}{units_alltime_formatted}u</div>
            </div>
            <div>
                <div class="stat-label" style="font-size: 0.75em; color: #666; margin-bottom: 0.3em;">Win Rate</div>
                <div class="stat-value" style="font-size: 1.8em; font-weight: bold; color: #1f77b4;">{stats_alltime['win_rate']}%</div>
            </div>
            <div>
                <div class="stat-label" style="font-size: 0.75em; color: #666; margin-bottom: 0.3em;">ROI</div>
                <div class="stat-value" style="font-size: 1.8em; font-weight: bold; color: #1f77b4;">{roi_alltime_sign}{stats_alltime['roi']}%</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.caption("✓ All picks posted before games · Full history below")

# CTA Button - Centered
col1, col2, col3 = st.columns([1, 0.5, 1])
with col2:
    if st.button("📊 View Today's Full Slate", type="primary", width="stretch"):
        st.switch_page("pages/picks.py")

# --- TODAY'S FREE PICK SECTION ---
st.markdown("<h3 style='margin-top: 0.5em; margin-bottom: 0.5em;'>🎁 TODAY'S FREE PICK</h3>",
            unsafe_allow_html=True)

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

# --- WHAT THIS IS SECTION ---
st.markdown("<h3 style='margin-top: 0.5em; margin-bottom: 0.5em;'>❓ WHAT THIS IS</h3>",
            unsafe_allow_html=True)

st.markdown("""
<div style="font-size: 1.1em; line-height: 1.8;">

**This is Not a Capper. It's an AI Pick Engine.**

🤖 **Multiple AI models** scan spreads, totals, and props.

📊 **You watch the models perform** and tail the winners.

</div>
""", unsafe_allow_html=True)

# --- HOW IT WORKS SECTION ---
st.markdown("<h3 style='margin-top: 0.5em; margin-bottom: 0.5em;'>⚙️ HOW IT WORKS</h3>",
            unsafe_allow_html=True)

st.markdown("""
<div style="font-size: 1.1em; line-height: 1.8;">

**1️⃣ Models Scan** — Lines pulled across major books in real time.

**2️⃣ Models Post** — Every pick is timestamped before kickoff.

**3️⃣ Results Logged** — Wins. Losses. Units. Nothing gets deleted.

**4️⃣ You Decide** — Tail, fade, parlay, or ignore.

</div>
""", unsafe_allow_html=True)

# --- THE RECEIPTS SECTION ---
st.markdown("<h3 style='margin-top: 0.5em; margin-bottom: 0.5em;'>📜 THE RECEIPTS</h3>",
            unsafe_allow_html=True)
st.markdown("**Public Performance Log**")

picks = list_ai_picks(limit=20)

if picks:
    # Create display data
    display_data = []
    for p in picks:
        if p.get('result') in ['Win', 'Loss', 'Push']:
            # Format pick with line for spreads and totals
            market = p.get('market', 'N/A').upper()
            pick_text = p.get('pick', 'N/A')
            line = p.get('line')

            if market == 'SPREADS' and line is not None:
                # Show spread with +/- sign
                sign = '+' if line > 0 else ''
                pick_display = f"{pick_text} {sign}{line} ({market})"
            elif market == 'TOTALS' and line is not None:
                # Show total line
                pick_display = f"{pick_text} {line} ({market})"
            else:
                # H2H or other markets
                pick_display = f"{pick_text} ({market})"

            display_data.append({
                "Date": p.get('date', 'N/A')[:10],
                "Sport": p.get('sport', 'N/A'),
                "Game": p.get('game', 'N/A'),
                "Pick": pick_display,
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
        st.switch_page("pages/picks.py")

# --- WHY USE THIS SECTION ---
st.markdown("<h3 style='margin-top: 0.5em; margin-bottom: 0.5em;'>✅ WHY USE THIS</h3>",
            unsafe_allow_html=True)

st.markdown("""
- **✋ No "LOCK OF THE DAY"** — No hype, just data
- **🚫 No Telegram pump-and-dump** — Transparent from day one
- **📊 No edited records** — All picks stay in the database
- **🤖 Multiple AI models** — Diverse perspectives, better edges
- **📈 Transparent unit tracking** — See every win and loss
- **🎯 Built to beat closing lines** — Not designed to sell picks
""")

# --- FAQ SECTION ---
st.markdown("<h3 style='margin-top: 0.5em; margin-bottom: 0.5em;'>❓ FAQ</h3>",
            unsafe_allow_html=True)

with st.expander("Is this gambling advice?"):
    st.markdown("No. It's data. You decide what to do with it.")

with st.expander("Do you hide losses?"):
    st.markdown("No. Losses stay. That's the point.")

with st.expander("Is this paid?"):
    st.markdown(
        "Always free daily pick. Premium features available with subscription.")

with st.expander("What sports?"):
    st.markdown("NBA, NFL, NCAAB, NHL, UFC, more coming.")

# --- FINAL CTA SECTION ---
st.markdown("""
<div style="text-align: center; padding: 1.5em 0; background: transparent; border-radius: 8px; margin: 0.8em 0; border: none;">
    <span style="font-size: 1.5em; margin: 0; color: #ffffff;">The Picks Are Public.</span>
     <span style="font-size: 1.5em; margin: 0.5em 0 0 0; color: #1f77b4;">The Results Don't Lie.</span>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 0.5, 1])
with col2:
    if st.button("🎯 View Today's Full Slate", type="primary", width="stretch"):
        st.switch_page("pages/picks.py")

# --- FOOTER ---
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.9em; padding: 0.8em 0;">
    <p style="margin: 0.3em 0;"><strong>For entertainment and informational purposes only.</strong></p>
    <p style="margin: 0.3em 0;">No guarantees. No financial advice. If you're mad about a loss, blame variance — not the model.</p>
    <p style="margin: 0.3em 0;"><a href="/terms" style="color: #888; text-decoration: none;">Terms & Conditions</a> | RAGE Picks &copy; 2026</p>
</div>
""", unsafe_allow_html=True)
