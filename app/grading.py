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

                # Extract team names from API response
                api_home_team = g.get("home_team", "")
                api_away_team = g.get("away_team", "")

                # Extract team names from our pick (format: "Away Team @ Home Team")
                if ' @ ' not in row["game"]:
                    continue
                pick_away_team, pick_home_team = row["game"].split(' @ ')

                # BULLETPROOF MATCHING: Ensure exact team match (both home AND away)
                # This prevents matching wrong games with similar team names
                home_match = api_home_team in pick_home_team or pick_home_team in api_home_team
                away_match = api_away_team in pick_away_team or pick_away_team in api_away_team

                if not (home_match and away_match):
                    continue

                # CRITICAL: Also match by date to prevent scoring wrong games
                game_commence = g.get("commence_time", "")
                game_date = game_commence[:10]  # Extract YYYY-MM-DD

                if game_date != pick_date:
                    logger.warning(
                        f"Date mismatch for {row['game']}: pick={pick_date}, game={game_date}")
                    continue

                # BULLETPROOF SCORE EXTRACTION
                # Extract scores by matching team names from the scores array
                # The API returns: "scores": [{"name": "Team Name", "score": "123"}, ...]
                home_score = None
                away_score = None

                for score_entry in g.get("scores", []):
                    score_team_name = score_entry.get("name", "")
                    score_value = score_entry.get("score")

                    # Match to home team
                    if score_team_name == api_home_team:
                        home_score = score_value
                    # Match to away team
                    elif score_team_name == api_away_team:
                        away_score = score_value

                # Validate we got both scores
                if home_score is None or away_score is None:
                    logger.warning(
                        f"Missing scores for {row['game']}: home={home_score}, away={away_score}")
                    logger.warning(
                        f"API data - home_team: {api_home_team}, away_team: {api_away_team}")
                    logger.warning(
                        f"Scores array: {g.get('scores', [])}")
                    continue

                # CRITICAL VALIDATION: Ensure scores are passed in correct order
                # _check_pick_result expects (pick_dict, home_score, away_score)
                # Our pick format is "Away @ Home", so we must pass home_score first
                try:
                    hs = int(home_score)
                    as_ = int(away_score)
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Invalid score format for {row['game']}: home={home_score}, away={away_score}, error={e}")
                    continue

                # Log the grading details for debugging
                logger.info(
                    f"Grading pick {row['id']}: {row['game']}")
                logger.info(
                    f"  API teams: {api_away_team} @ {api_home_team}")
                logger.info(
                    f"  Scores: Away={as_}, Home={hs}")
                logger.info(
                    f"  Pick: {row['pick']} {row['market']} {row.get('line', 'N/A')}")

                # Convert to dict for helper function
                pick_dict = {
                    'game': row['game'],
                    'pick': row['pick'],
                    'market': row['market'],
                    'line': row['line']
                }

                result = _check_pick_result(pick_dict, hs, as_)

                if result != 'Pending':
                    logger.info(
                        f"  Result: {result}")
                    cur.execute("UPDATE ai_picks SET result=? WHERE id=?",
                                (result, row["id"]))
                    updated += 1
                else:
                    logger.info("  Result: still pending")
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

                # Extract team names from API response
                api_home_team = g.get("home_team", "")
                api_away_team = g.get("away_team", "")

                # Extract team names from leg game (format: "Away Team @ Home Team")
                if ' @ ' not in leg_game:
                    continue
                leg_away_team, leg_home_team = leg_game.split(' @ ')

                # BULLETPROOF MATCHING: Ensure exact team match (both home AND away)
                home_match = api_home_team in leg_home_team or leg_home_team in api_home_team
                away_match = api_away_team in leg_away_team or leg_away_team in api_away_team

                if not (home_match and away_match):
                    continue

                # BULLETPROOF SCORE EXTRACTION for parlay leg
                home_score = None
                away_score = None

                for score_entry in g.get("scores", []):
                    score_team_name = score_entry.get("name", "")
                    score_value = score_entry.get("score")

                    # Match to home team
                    if score_team_name == api_home_team:
                        home_score = score_value
                    # Match to away team
                    elif score_team_name == api_away_team:
                        away_score = score_value

                # Validate we got both scores
                if home_score is None or away_score is None:
                    logger.warning(
                        f"Missing scores for parlay leg {leg_game}: home={home_score}, away={away_score}")
                    continue

                # Convert scores to integers with validation
                try:
                    hs = int(home_score)
                    as_ = int(away_score)
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Invalid score format for parlay leg {leg_game}: home={home_score}, away={away_score}, error={e}")
                    continue

                leg_pick_dict = {
                    'game': leg_game,
                    'pick': leg.get('pick'),
                    'market': leg.get('market'),
                    'line': leg.get('line')
                }

                # Log parlay leg grading
                logger.info(
                    f"Grading parlay leg: {leg_game}")
                logger.info(
                    f"  API teams: {api_away_team} @ {api_home_team}")
                logger.info(
                    f"  Scores: Away={as_}, Home={hs}")

                leg_result = _check_pick_result(leg_pick_dict, hs, as_)
                logger.info(
                    f"  Leg result: {leg_result}")
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
