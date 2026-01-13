# pages/admin_manual_picks.py
import streamlit as st
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.auth import add_auth_to_page, is_admin
from app.db import insert_ai_pick, list_ai_picks, delete_ai_pick
from app.rage_picks import fetch_odds


# -----------------------------
# Helper Functions
# -----------------------------
def american_to_decimal(american_odds):
    """Convert American odds to decimal odds."""
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def decimal_to_american(decimal_odds):
    """Convert decimal odds to American odds."""
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))


def calculate_parlay_odds(picks_odds_list):
    """
    Calculate parlay odds from a list of American odds.
    Returns American odds for the parlay.
    """
    if not picks_odds_list:
        return 0

    # Convert all to decimal and multiply
    decimal_odds = 1.0
    for american_odds in picks_odds_list:
        decimal_odds *= american_to_decimal(american_odds)

    # Convert back to American
    return decimal_to_american(decimal_odds)


# -----------------------------
# Authentication & Admin Check
# -----------------------------
add_auth_to_page()

# Check if user is admin
if not is_admin():
    st.error("🚫 Access Denied: Admin only")
    st.stop()

# --- Hide Streamlit's default page navigation ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# --- Inline Navigation (Public) ---
st.markdown("""
<div style="text-align: center; margin-bottom: 2em; font-size: 1.05em; font-weight: 500;">
    Navigation: Home | RAGE Picks | Live Scores
</div>
""", unsafe_allow_html=True)

# --- Admin Section ---
st.sidebar.markdown("### ⚙️ Admin")
st.sidebar.page_link("pages/admin_manual_picks.py",
                     label="Manual Picks", icon="🔧")

# -----------------------------
# Page Configuration
# -----------------------------
st.set_page_config(page_title="🔧 Admin: Manual Picks", layout="wide")
st.title("🔧 Admin: Manual Picks Entry")
st.markdown(
    "Add manual picks from other cappers and sources. These will appear alongside AI picks.")

# Initialize session state for parlay builder
if 'parlay_picks' not in st.session_state:
    st.session_state.parlay_picks = []

# -----------------------------
# Parlay Builder Section
# -----------------------------
with st.expander("🎰 Parlay Builder (Combine up to 6 picks)", expanded=False):
    st.markdown("### Build a Parlay")
    st.caption(
        "Add individual picks to build a parlay. The odds will be automatically calculated.")

    # Display current parlay picks
    if st.session_state.parlay_picks:
        st.markdown(
            f"**Current Parlay ({len(st.session_state.parlay_picks)}/6 picks):**")

        for idx, pick in enumerate(st.session_state.parlay_picks, 1):
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.markdown(f"**{idx}.** {pick['sport']} - {pick['game']}")
                st.caption(
                    f"{pick['pick']} ({pick['market']}) @ {pick['line']}")
            with col2:
                st.markdown(f"**Odds:** {pick['odds']:+d}")
            with col3:
                if st.button("❌", key=f"remove_parlay_{idx}", help="Remove from parlay"):
                    st.session_state.parlay_picks.pop(idx - 1)
                    st.rerun()

        # Calculate parlay odds
        parlay_odds_list = [p['odds'] for p in st.session_state.parlay_picks]
        parlay_odds = calculate_parlay_odds(parlay_odds_list)

        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Picks", len(st.session_state.parlay_picks))
        with col2:
            st.metric("Parlay Odds", f"{parlay_odds:+d}")
        with col3:
            # Calculate potential payout on $100 bet
            if parlay_odds > 0:
                payout = 100 + (parlay_odds / 100 * 100)
            else:
                payout = 100 + (100 / abs(parlay_odds) * 100)
            st.metric("$100 Payout", f"${payout:.2f}")

        # Add parlay to database button
        parlay_confidence = st.selectbox(
            "Parlay Confidence", [3, 4, 5], index=1, key="parlay_confidence")

        if st.button("✅ Save Parlay to Database", type="primary", use_container_width=True):
            # Combine all picks into one entry
            import json

            games_list = [p['game'] for p in st.session_state.parlay_picks]
            picks_list = [
                f"{p['pick']} ({p['market']})" for p in st.session_state.parlay_picks]

            # Store structured parlay leg data as JSON for result checking
            parlay_legs = []
            for p in st.session_state.parlay_picks:
                leg = {
                    "game": p['game'],
                    "sport": p['sport'],
                    "pick": p['pick'],
                    "market": p['market'],
                    "line": p.get('line'),
                    "commence_time": p['commence_time']
                }
                parlay_legs.append(leg)

            parlay_data = {
                "game": " | ".join(games_list),
                "sport": "PARLAY",  # Special sport type for parlays
                "pick": " + ".join(picks_list),
                "market": "parlay",
                "line": None,
                "odds_american": parlay_odds,
                "confidence": str(parlay_confidence),
                # Store parlay legs as JSON in reasoning field for result checking
                "reasoning": json.dumps({"legs": parlay_legs, "description": f"Parlay ({len(st.session_state.parlay_picks)} picks): " + " | ".join([f"{p['sport']}: {p['pick']}" for p in st.session_state.parlay_picks])}),
                # Use first game's time
                "commence_time": st.session_state.parlay_picks[0]['commence_time'],
                "result": "Pending",
                "source": "RAGE"
            }

            insert_ai_pick(parlay_data)
            st.success(
                f"✅ Parlay saved! {len(st.session_state.parlay_picks)} picks @ {parlay_odds:+d}")
            st.balloons()

            # Clear parlay
            st.session_state.parlay_picks = []
            st.rerun()

        if st.button("🗑️ Clear Parlay", type="secondary"):
            st.session_state.parlay_picks = []
            st.rerun()
    else:
        st.info("👆 Add picks below to build a parlay. You can combine up to 6 picks.")

st.markdown("---")

# -----------------------------
# Manual Pick Entry Form
# -----------------------------
st.header("Add New Manual Pick")

# Sport Selection
sports_map = {
    "NFL": "americanfootball_nfl",
    "NCAAF": "americanfootball_ncaaf",
    "NCAAB": "basketball_ncaab",
    "NBA": "basketball_nba",
    "NHL": "icehockey_nhl",
}

col1, col2 = st.columns(2)

with col1:
    sport_name = st.selectbox("1️⃣ Select Sport", list(sports_map.keys()))
    sport_key = sports_map[sport_name]

with col2:
    confidence = st.selectbox("2️⃣ Confidence (Stars)", [3, 4, 5], index=1)

# Fetch games for selected sport
if st.button("🔄 Fetch Games", type="secondary"):
    with st.spinner(f"Fetching {sport_name} games..."):
        games_data = fetch_odds(sport_key)
        st.session_state.games_data = games_data
        if games_data:
            st.success(f"✅ Found {len(games_data)} upcoming games")
        else:
            st.warning("⚠️ No upcoming games found for this sport")

# Game Selection
if 'games_data' in st.session_state and st.session_state.games_data:
    games_data = st.session_state.games_data

    # Format game options
    game_options = {}
    for game in games_data:
        game_label = f"{game['away_team']} @ {game['home_team']}"
        try:
            dt_utc = datetime.fromisoformat(
                game['commence_time'].replace('Z', '+00:00'))
            if dt_utc.tzinfo is None:
                dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            local_tz = ZoneInfo("America/Los_Angeles")
            dt_local = dt_utc.astimezone(local_tz)
            game_label += f" - {dt_local.strftime('%a %b %d, %I:%M %p')}"
        except (KeyError, ValueError, TypeError, AttributeError):
            pass
        game_options[game_label] = game

    selected_game_label = st.selectbox(
        "3️⃣ Select Game", list(game_options.keys()))
    selected_game = game_options[selected_game_label]

    # Market Selection
    market_key = st.selectbox("4️⃣ Select Market", [
                              "h2h", "spreads", "totals"])

    # Find odds data for selected market
    odds_data = None
    for bookmaker in selected_game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == market_key:
                odds_data = market
                break
        if odds_data:
            break

    if odds_data and odds_data.get("outcomes"):
        # Format outcome choices
        if market_key in ["spreads", "totals"]:
            outcomes = {
                f"{o['name']} {o.get('point', '')} @ {o['price']}": o
                for o in odds_data["outcomes"]
            }
        else:  # h2h
            outcomes = {
                f"{o['name']} @ {o['price']}": o
                for o in odds_data["outcomes"]
            }

        pick_label = st.selectbox("5️⃣ Select Pick", list(outcomes.keys()))
        picked_outcome = outcomes[pick_label]

        # --- Point Buying Feature (for spreads/totals only) ---
        adjusted_line = picked_outcome.get('point')
        adjusted_odds = picked_outcome['price']
        point_adjustment = 0

        if market_key in ["spreads", "totals"]:
            st.markdown("---")
            st.subheader("🎯 Optional: Buy Points")
            st.caption(
                "Adjust the line by buying points. Odds will be adjusted accordingly.")

            point_adjustment = st.slider(
                "Buy Points (-2 to +2)",
                min_value=-2.0,
                max_value=2.0,
                value=0.0,
                step=0.5,
                help="Negative = buy points in your favor (worse odds), Positive = sell points (better odds)"
            )

            if point_adjustment != 0:
                # Calculate adjusted line
                original_line = float(picked_outcome.get('point', 0))
                adjusted_line = original_line + point_adjustment

                # Estimate odds adjustment (rough approximation)
                # Each half point typically costs about 10-20 points of juice
                # Buying points (negative adjustment) = worse odds
                # Selling points (positive adjustment) = better odds
                odds_adjustment_per_half_point = 15  # Average adjustment
                total_odds_adjustment = int(
                    point_adjustment * odds_adjustment_per_half_point * 2)

                # Apply adjustment to American odds
                original_odds = picked_outcome['price']
                if original_odds < 0:
                    # Favorite: buying points makes it more negative (worse)
                    adjusted_odds = original_odds - total_odds_adjustment
                else:
                    # Underdog: buying points makes it less positive (worse)
                    adjusted_odds = original_odds - total_odds_adjustment

                # Display adjustment info
                st.info(
                    f"📊 Adjusted Line: **{adjusted_line}** (was {original_line})")
                st.info(
                    f"💰 Adjusted Odds: **{adjusted_odds:+d}** (was {original_odds:+d})")

        # Display pick summary
        st.markdown("---")
        st.subheader("📋 Pick Summary")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Sport", sport_name)
            st.metric(
                "Game", f"{selected_game['away_team']} @ {selected_game['home_team']}")
        with col2:
            st.metric("Market", market_key.upper())
            st.metric("Pick", picked_outcome['name'])
        with col3:
            # Show adjusted line and odds if points were bought
            display_line = adjusted_line if adjusted_line is not None else 'ML'
            st.metric("Line", display_line)
            st.metric("Odds", f"{adjusted_odds:+d}" if isinstance(
                adjusted_odds, (int, float)) else adjusted_odds)
            st.metric("Confidence", "⭐" * confidence)

        # Show point adjustment note if applicable
        if point_adjustment != 0:
            st.warning(
                f"⚠️ Points adjusted: {point_adjustment:+.1f} (Line: {picked_outcome.get('point')} → {adjusted_line})")

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            # Add to Parlay button
            can_add_to_parlay = len(st.session_state.parlay_picks) < 6
            if st.button("🎰 Add to Parlay", type="secondary", use_container_width=True, disabled=not can_add_to_parlay):
                # Prepare pick data for parlay
                parlay_pick = {
                    "game": f"{selected_game['away_team']} @ {selected_game['home_team']}",
                    "sport": sport_name,
                    "pick": picked_outcome['name'],
                    "market": market_key,
                    "line": adjusted_line if adjusted_line is not None else 'ML',
                    "odds": int(adjusted_odds),
                    "commence_time": selected_game['commence_time']
                }

                st.session_state.parlay_picks.append(parlay_pick)
                st.success(
                    f"✅ Added to parlay! ({len(st.session_state.parlay_picks)}/6)")
                st.rerun()

            if not can_add_to_parlay:
                st.caption("⚠️ Parlay is full (6/6)")

        with col2:
            # Add Pick Button (single pick)
            if st.button("✅ Add Pick to Database", type="primary", use_container_width=True):
                # Prepare reasoning with point adjustment info
                reasoning = "High confidence pick from expert source"
                if point_adjustment != 0:
                    reasoning += f" (bought {point_adjustment:+.1f} points)"

                # Prepare pick data with adjusted values
                pick_data = {
                    "game": f"{selected_game['away_team']} @ {selected_game['home_team']}",
                    "sport": sport_name,
                    "pick": picked_outcome['name'],
                    "market": market_key,
                    "line": adjusted_line,  # Use adjusted line
                    "odds_american": adjusted_odds,  # Use adjusted odds
                    "confidence": str(confidence),
                    "reasoning": reasoning,
                    "commence_time": selected_game['commence_time'],
                    "result": "Pending",
                    "source": "RAGE"
                }

                # Insert into database
                insert_ai_pick(pick_data)
                st.success(
                    f"✅ Successfully added {sport_name} pick: {picked_outcome['name']}")
                st.balloons()

                # Clear session state
                if 'games_data' in st.session_state:
                    del st.session_state.games_data
                st.rerun()
    else:
        st.warning(f"⚠️ No odds available for {market_key} market")
else:
    st.info("👆 Click 'Fetch Games' to load available games")

# -----------------------------
# View & Delete Manual Picks
# -----------------------------
st.markdown("---")
st.header("📜 Manage Manual Picks")

# Get all RAGE picks
all_picks = list_ai_picks(limit=200)
rage_picks = [p for p in all_picks if p.get('source') == 'RAGE']

if rage_picks:
    st.markdown(f"**Total Manual Picks:** {len(rage_picks)}")

    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_sport = st.selectbox(
            "Filter by Sport", ["All"] + list(sports_map.keys()), key="filter_sport")
    with filter_col2:
        filter_result = st.selectbox("Filter by Result", [
                                     "All", "Pending", "Win", "Loss", "Push"], key="filter_result")

    # Apply filters
    filtered_picks = rage_picks
    if filter_sport != "All":
        filtered_picks = [p for p in filtered_picks if p.get(
            'sport') == filter_sport]
    if filter_result != "All":
        filtered_picks = [p for p in filtered_picks if p.get(
            'result', 'Pending') == filter_result]

    st.markdown(f"**Showing:** {len(filtered_picks)} picks")

    # Display picks in a table format with delete buttons
    for pick in filtered_picks:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 0.5])

            with col1:
                st.markdown(f"**{pick.get('sport')}** - {pick.get('game')}")
                try:
                    dt_utc = datetime.fromisoformat(
                        pick.get('date', '').replace('Z', '+00:00'))
                    if dt_utc.tzinfo is None:
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                    local_tz = ZoneInfo("America/Los_Angeles")
                    dt_local = dt_utc.astimezone(local_tz)
                    st.caption(dt_local.strftime('%a, %b %d, %I:%M %p PT'))
                except (ValueError, TypeError, AttributeError):
                    st.caption(pick.get('date', 'N/A'))

            with col2:
                st.markdown(f"**Pick:** {pick.get('pick')}")
                st.caption(
                    f"{pick.get('market')} | Line: {pick.get('line', 'ML')} | Odds: {pick.get('odds_american')}")

            with col3:
                confidence_stars = "⭐" * int(pick.get('confidence', 3))
                st.markdown(f"**{confidence_stars}**")

            with col4:
                result = pick.get('result', 'Pending')
                if result == 'Win':
                    st.success(f"✅ {result}")
                elif result == 'Loss':
                    st.error(f"❌ {result}")
                elif result == 'Push':
                    st.warning(f"↔️ {result}")
                else:
                    st.info(f"⏳ {result}")

            with col5:
                if st.button("🗑️", key=f"delete_rage_{pick['id']}", help=f"Delete pick #{pick['id']}"):
                    if delete_ai_pick(pick['id']):
                        st.success(f"✅ Deleted pick #{pick['id']}")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to delete pick #{pick['id']}")
else:
    st.info("No manual picks found. Add your first pick above!")
