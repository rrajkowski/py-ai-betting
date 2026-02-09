"""
AI pick generation and validation logic.

Handles multi-model LLM fallback, deduplication, conflict detection,
and consensus validation for sports betting picks.
"""

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from .db import get_db, insert_ai_picks
from .llm import _call_claude_model, _call_gemini_model, _call_openai_model

logger = logging.getLogger(__name__)


def normalize_pick_team(pick_str, line_val):
    """
    Normalize a pick string to extract just the team name.
    Handles cases like:
    - "Tulane Green Wave +17.5" -> "tulane green wave"
    - "Ole Miss Rebels -3.5" -> "ole miss rebels"
    """
    pick_normalized = pick_str.lower().strip()

    # Remove line value if present (e.g., "+17.5", "-3.5", "17.5")
    if line_val is not None:
        patterns = [
            rf'\s*\+?\-?{re.escape(str(line_val))}\s*$',
            rf'\s*\+{re.escape(str(abs(float(line_val))))}\s*$',
            rf'\s*\-{re.escape(str(abs(float(line_val))))}\s*$',
        ]
        for pattern in patterns:
            pick_normalized = re.sub(pattern, '', pick_normalized)

    # Remove any remaining +/- signs at the end
    pick_normalized = re.sub(r'\s*[\+\-]\s*$', '', pick_normalized)

    return pick_normalized.strip()


def is_conflicting_pick(game, market, pick_value, line, existing_picks_list):
    """Check if a pick conflicts with existing picks for the same game+market."""
    market_lower = market.lower()
    pick_lower = pick_value.lower()

    for existing_pick, existing_line in existing_picks_list:
        existing_pick_lower = existing_pick.lower()

        # Spread: Can't pick both teams (opposite signs) OR same team with same/similar line
        if market_lower == 'spreads':
            try:
                new_line_val = float(str(line).replace('+', ''))
                existing_line_val = float(
                    str(existing_line).replace('+', ''))

                new_team = normalize_pick_team(pick_value, line)
                existing_team = normalize_pick_team(
                    existing_pick, existing_line)

                if new_team == existing_team and abs(new_line_val) == abs(existing_line_val):
                    return True

                if (new_line_val > 0 and existing_line_val < 0) or (new_line_val < 0 and existing_line_val > 0):
                    return True
            except (ValueError, TypeError):
                pass

        # Totals: Can't pick both Over AND Under
        elif market_lower == 'totals':
            if (pick_lower == 'over' and existing_pick_lower == 'under') or \
               (pick_lower == 'under' and existing_pick_lower == 'over'):
                return True

        # H2H/Moneyline: Can't pick both teams
        elif market_lower == 'h2h' and pick_lower != existing_pick_lower:
            return True

    return False


def validate_pick_against_consensus(pick, context_payload):
    """
    Validates that the AI's pick matches the consensus direction.
    Returns (is_valid, reason) tuple.
    """
    game = pick.get('game', '')
    market = pick.get('market', '').lower()
    pick_value = pick.get('pick', '').lower()

    # Find this game in the context
    games = context_payload.get('games', [])
    game_context = None
    for g in games:
        if g.get('game_id', '') == game:
            game_context = g
            break

    if not game_context:
        return (True, "No context found")

    expert_consensus = game_context.get(
        'context', {}).get('expert_consensus', [])

    if not expert_consensus:
        return (True, "No consensus data")

    # For totals, check if consensus direction matches pick direction
    if market == 'totals':
        consensus_directions = []
        for expert in expert_consensus:
            if isinstance(expert, dict):
                direction = expert.get('direction', '').lower()
                if not direction and 'pick' in expert:
                    pick_text = expert.get('pick', '').lower()
                    if 'over' in pick_text:
                        direction = 'over'
                    elif 'under' in pick_text:
                        direction = 'under'

                if direction in ['over', 'under']:
                    consensus_directions.append(direction)

        if consensus_directions:
            over_count = consensus_directions.count('over')
            under_count = consensus_directions.count('under')

            if over_count > under_count:
                consensus_dir = 'over'
            elif under_count > over_count:
                consensus_dir = 'under'
            else:
                return (True, "Consensus is split")

            if pick_value != consensus_dir:
                return (False, f"Pick is {pick_value} but consensus is {consensus_dir} ({over_count} over, {under_count} under)")

    return (True, "Validated")


def generate_ai_picks(odds_df, history_data, sport="unknown", context_payload=None, kalshi_context=None):
    # Lazy import to avoid circular dependency
    from .rage_picks import _safe_parse_datetime

    context = {
        "odds_count": len(odds_df),
        "sport": sport.upper(),
        "sample_odds": odds_df.head(15).to_dict(orient="records"),
        "history": history_data,
    }
    if context_payload:
        context["extra_context"] = context_payload
    if kalshi_context:
        context["kalshi"] = kalshi_context

    # Load prompt from external file for easier iteration
    prompt_path = Path(__file__).parent.parent / "prompts" / "picks_prompt.txt"
    with open(prompt_path) as f:
        prompt_template = f.read()

    prompt = prompt_template.replace(
        "{context_json}", json.dumps(context, indent=2))

    # Model priority order: Best reasoning → Fast fallback → Emergency fallback
    models = [
        {'provider': 'anthropic', 'name': 'claude-sonnet-4-5-20250929'},
        {'provider': 'google', 'name': 'gemini-2.5-pro'},
        {'provider': 'openai', 'name': 'gpt-5'},
        {'provider': 'anthropic', 'name': 'claude-haiku-4-5-20251001'},
        {'provider': 'google', 'name': 'gemini-2.5-flash'},
        {'provider': 'openai', 'name': 'gpt-5-mini'},
        {'provider': 'openai', 'name': 'gpt-5-nano'},
        {'provider': 'google', 'name': 'gemini-2.5-flash-lite'},
    ]

    parsed = []
    for idx, m in enumerate(models):
        try:
            if m['provider'] == 'google':
                parsed = _call_gemini_model(m['name'], prompt)
            elif m['provider'] == 'openai':
                parsed = _call_openai_model(m['name'], prompt)
            elif m['provider'] == 'anthropic':
                parsed = _call_claude_model(m['name'], prompt)
            else:
                st.warning(f"Unknown provider: {m['provider']}")
                continue

            if parsed:
                st.success(
                    f"✅ Generated {len(parsed)} picks using {m['provider']}:{m['name']}")
                break
        except Exception as e:
            st.warning(
                f"⚠️ {m['provider']}:{m['name']} failed: {str(e)[:100]}")
            if idx < len(models) - 1:
                import time
                time.sleep(1)
            continue

    if not parsed:
        st.error("All models failed to generate picks.")
        return []

    # Get existing picks from database to avoid duplicates and conflicts
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT game, market, pick, line FROM ai_picks
            WHERE result = 'Pending'
            AND datetime(commence_time) > datetime('now')
        """)
        existing_picks = set()
        existing_game_markets = {}
        for row in cur.fetchall():
            game = row[0].strip() if row[0] else ""
            market = row[1].strip() if row[1] else ""
            pick = row[2].strip() if row[2] else ""
            line = row[3]

            existing_picks.add((game, market, pick, line))

            key = (game, market)
            if key not in existing_game_markets:
                existing_game_markets[key] = []
            existing_game_markets[key].append((pick, line))

    unique_picks = []
    seen_game_markets = {}
    skipped_duplicates = 0
    skipped_conflicts = 0

    for pick in parsed:
        pick.setdefault("sport", sport)
        dt = _safe_parse_datetime(
            pick.get('commence_time') or pick.get('date'))
        if not dt:
            st.warning(
                f"⏰ Missing commence_time for {pick.get('game')}, defaulting to now()")
            dt = datetime.now(UTC)
            pick['commence_time'] = dt.isoformat()

        try:
            if int(pick.get("confidence", 0)) < 3:
                continue
        except (ValueError, TypeError):
            continue

        # CRITICAL: Validate odds are within acceptable range (-150 to +150)
        odds = pick.get("odds_american")
        if odds is not None:
            try:
                odds_val = float(odds)
                if odds_val < -150 or odds_val > 150:
                    st.warning(
                        f"⚠️ REJECTING {pick.get('game')} - {pick.get('pick')}: Odds {odds_val} outside acceptable range (-150 to +150)")
                    continue
            except (ValueError, TypeError):
                pass

        # Validate pick against consensus direction
        is_valid, reason = validate_pick_against_consensus(
            pick, context_payload)
        if not is_valid:
            st.warning(
                f"⚠️ Skipping {pick.get('game')} - {pick.get('pick')}: {reason}")
            continue

        game = pick.get('game', '').strip()
        market = pick.get('market', '').strip()
        pick_value = pick.get('pick', '').strip()
        line = pick.get('line')

        pick_signature = (game, market, pick_value, line)
        if pick_signature in existing_picks:
            skipped_duplicates += 1
            continue

        game_market_key = (game, market)
        if game_market_key in existing_game_markets and is_conflicting_pick(game, market, pick_value, line, existing_game_markets[game_market_key]):
            skipped_conflicts += 1
            continue

        if game_market_key in seen_game_markets and is_conflicting_pick(game, market, pick_value, line, seen_game_markets[game_market_key]):
            skipped_conflicts += 1
            continue

        if game_market_key not in seen_game_markets:
            seen_game_markets[game_market_key] = []
        seen_game_markets[game_market_key].append((pick_value, line))

        unique_picks.append(pick)

    if skipped_duplicates > 0:
        st.info(
            f"⏭️ Skipped {skipped_duplicates} duplicate pick(s) already in database")
    if skipped_conflicts > 0:
        st.info(
            f"⏭️ Skipped {skipped_conflicts} conflicting pick(s) for games with existing picks")

    if unique_picks:
        insert_ai_picks(unique_picks)
        st.toast(f"Saved {len(unique_picks)} new picks.")
    else:
        st.toast("No new picks to save.")

    return parsed
