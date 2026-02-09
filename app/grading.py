"""
Auto-grading logic for AI-generated sports picks.

Determines if picks won, lost, or pushed based on final scores.
"""

import json
import logging
from datetime import UTC, datetime

from .db import get_db

logger = logging.getLogger(__name__)


def _check_pick_result(pick_dict, home_score, away_score):
    """
    Determines if a single pick (H2H, Spread, or Total) won, lost, or pushed.
    Returns 'Win', 'Loss', 'Push', or 'Pending'.

    Args:
        pick_dict: Dictionary with keys: 'pick', 'market', 'line', 'sport'
        home_score: Integer home team/fighter score
        away_score: Integer away team/fighter score
    """
    if home_score is None or away_score is None:
        return 'Pending'

    market = pick_dict.get('market', '').lower()

    # Handle h2h (moneyline)
    if market == 'h2h':
        game = pick_dict.get('game', '')
        if ' @ ' not in game:
            return 'Pending'

        away_team, home_team = game.split(' @ ')

        # For UFC/MMA, scores are 1 (winner) or 0 (loser)
        # For other sports, scores are numeric (e.g., 10-5)
        if home_score > away_score:
            winner = home_team
        elif away_score > home_score:
            winner = away_team
        else:
            return 'Push'

        return 'Win' if pick_dict['pick'] == winner else 'Loss'

    # Handle spreads
    elif market == 'spreads':
        line = pick_dict.get('line')
        if line is None:
            return 'Pending'

        game = pick_dict.get('game', '')
        if ' @ ' not in game:
            return 'Pending'

        away_team, home_team = game.split(' @ ')

        # Determine if pick is for home or away team
        if pick_dict['pick'] == home_team:
            adjusted_score = home_score + line
            opponent_score = away_score
        elif pick_dict['pick'] == away_team:
            adjusted_score = away_score + line
            opponent_score = home_score
        else:
            return 'Pending'

        if adjusted_score > opponent_score:
            return 'Win'
        elif adjusted_score < opponent_score:
            return 'Loss'
        else:
            return 'Push'

    # Handle totals (over/under)
    elif market == 'totals':
        line = pick_dict.get('line')
        if line is None:
            return 'Pending'

        total_score = home_score + away_score
        pick = pick_dict.get('pick', '').lower()

        if pick == 'over':
            if total_score > line:
                return 'Win'
            elif total_score < line:
                return 'Loss'
            else:
                return 'Push'
        elif pick == 'under':
            if total_score < line:
                return 'Win'
            elif total_score > line:
                return 'Loss'
            else:
                return 'Push'

    return 'Pending'


def update_ai_pick_results():
    """Grade all pending AI picks against actual game results."""
    # Lazy imports to avoid circular dependency with rage_picks
    from .rage_picks import _safe_parse_datetime, fetch_scores

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, game, pick, market, line, sport, commence_time, reasoning FROM ai_picks WHERE LOWER(result)='pending'")
        pending = cur.fetchall()
        if not pending:
            logger.info("No pending picks to update.")
            return

        logger.info(f"Checking {len(pending)} pending picks...")
        updated = 0
        skipped_not_started = 0
        skipped_not_completed = 0

        for row in pending:
            commence = row["commence_time"]
            dt = _safe_parse_datetime(commence)
            if not dt:
                logger.warning(
                    f"Could not parse commence_time for pick {row['id']}: {commence}")
                continue

            # Skip games that haven't started yet
            if datetime.now(UTC) < dt:
                skipped_not_started += 1
                continue

            # Extract the date from the pick's commence_time (YYYY-MM-DD)
            pick_date = dt.strftime('%Y-%m-%d')

            # Handle PARLAY picks separately
            sport = row["sport"]
            if sport == "PARLAY":
                parlay_result = _grade_parlay_pick(row, cur, fetch_scores)
                if parlay_result == "updated":
                    updated += 1
                elif parlay_result == "skipped":
                    skipped_not_completed += 1
                continue

            # Map sport name to API key for regular picks
            if sport == "NFL":
                sport_key = "americanfootball_nfl"
            elif sport == "NCAAF":
                sport_key = "americanfootball_ncaaf"
            elif sport == "NCAAB":
                sport_key = "basketball_ncaab"
            elif sport == "NBA":
                sport_key = "basketball_nba"
            elif sport == "NHL":
                sport_key = "icehockey_nhl"
            else:
                continue

            scores = fetch_scores(sport=sport_key, days_from=2)
            if not scores:
                continue

            for g in scores:
                # CRITICAL: Only process completed games
                if not g.get("completed"):
                    continue

                # Match by team names
                if g.get("home_team") in row["game"] and g.get("away_team") in row["game"]:
                    # CRITICAL: Also match by date to prevent scoring wrong games
                    game_commence = g.get("commence_time", "")
                    game_date = game_commence[:10]  # Extract YYYY-MM-DD

                    if game_date != pick_date:
                        logger.warning(
                            f"Date mismatch for {row['game']}: pick={pick_date}, game={game_date}")
                        continue

                    home, away = g["home_team"], g["away_team"]
                    hs = next((s["score"]
                              for s in g["scores"] if s["name"] == home), None)
                    as_ = next((s["score"]
                               for s in g["scores"] if s["name"] == away), None)
                    if hs is None or as_ is None:
                        logger.warning(
                            f"Missing scores for {row['game']}: home={hs}, away={as_}")
                        continue

                    # Convert to dict for helper function
                    pick_dict = {
                        'game': row['game'],
                        'pick': row['pick'],
                        'market': row['market'],
                        'line': row['line']
                    }

                    result = _check_pick_result(pick_dict, int(hs), int(as_))

                    if result != 'Pending':
                        logger.info(
                            f"Scoring pick {row['id']}: {row['game']} - {row['pick']} ({row['market']}) = {result}")
                        cur.execute("UPDATE ai_picks SET result=? WHERE id=?",
                                    (result, row["id"]))
                        updated += 1
                    else:
                        logger.info(f"Result still pending for {row['game']}")
                    break

        conn.commit()
        logger.info(
            f"Updated {updated} picks. Skipped {skipped_not_started} not started, {skipped_not_completed} not completed.")


def _grade_parlay_pick(row, cur, fetch_scores):
    """
    Grade a single PARLAY pick by checking each leg against scores.

    Returns:
        'updated' if parlay was scored, 'skipped' if incomplete, None otherwise.
    """
    try:
        reasoning_data = json.loads(row["reasoning"])
        parlay_legs = reasoning_data.get("legs", [])

        if not parlay_legs:
            logger.warning(f"Parlay {row['id']} has no legs data")
            return None

        # Check each leg's result
        leg_results = []
        all_legs_completed = True

        for leg in parlay_legs:
            leg_sport = leg.get("sport")
            leg_game = leg.get("game")

            # Map sport to API key
            sport_map = {
                "NFL": "americanfootball_nfl",
                "NCAAF": "americanfootball_ncaaf",
                "NCAAB": "basketball_ncaab",
                "NBA": "basketball_nba",
                "NHL": "icehockey_nhl",
            }
            sport_key = sport_map.get(leg_sport)
            if not sport_key:
                logger.warning(
                    f"Unknown sport in parlay leg: {leg_sport}")
                all_legs_completed = False
                break

            # Fetch scores for this leg's sport
            scores = fetch_scores(sport=sport_key, days_from=2)
            if not scores:
                all_legs_completed = False
                break

            # Find the matching game
            leg_result = None
            for g in scores:
                if not g.get("completed"):
                    continue

                if g.get("home_team") in leg_game and g.get("away_team") in leg_game:
                    home, away = g["home_team"], g["away_team"]
                    hs = next(
                        (s["score"] for s in g["scores"] if s["name"] == home), None)
                    as_ = next(
                        (s["score"] for s in g["scores"] if s["name"] == away), None)

                    if hs is None or as_ is None:
                        continue

                    leg_pick_dict = {
                        'game': leg_game,
                        'pick': leg.get('pick'),
                        'market': leg.get('market'),
                        'line': leg.get('line')
                    }
                    leg_result = _check_pick_result(
                        leg_pick_dict, int(hs), int(as_))
                    break

            if leg_result is None or leg_result == 'Pending':
                all_legs_completed = False
                break

            leg_results.append(leg_result)

        # Determine parlay result: all legs must win (or push) for parlay to win
        if all_legs_completed and len(leg_results) == len(parlay_legs):
            if all(r == 'Win' for r in leg_results):
                parlay_result = 'Win'
            elif any(r == 'Loss' for r in leg_results):
                parlay_result = 'Loss'
            else:
                parlay_result = 'Push'

            logger.info(
                f"Scoring parlay {row['id']}: {parlay_result} (legs: {leg_results})")
            cur.execute(
                "UPDATE ai_picks SET result=? WHERE id=?", (parlay_result, row["id"]))
            return "updated"
        else:
            logger.info(
                f"Parlay {row['id']} not all legs completed yet")
            return "skipped"

    except json.JSONDecodeError:
        logger.warning(
            f"Parlay {row['id']} uses old format - manual scoring required. "
            f"To manually score: UPDATE ai_picks SET result='Loss' WHERE id={row['id']};")
        return None
    except Exception as e:
        logger.error(f"Error processing parlay {row['id']}: {e}")
        return None
