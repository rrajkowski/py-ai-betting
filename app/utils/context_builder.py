from datetime import datetime
from app.utils.db import fetch_context_by_date  # Assumed to take (date, sport)

# Define the canonical structure for the AI super-prompt
CANONICAL_CONTEXT_STRUCTURE = {
    "expert_consensus": {},
    "public_consensus": {},
    "neutral_site": {},
    "coaching_factors": {},
    "ensemble_notes": {},
    "confidence_calibration": {}
}


def build_merged_context(target_date: str, sport: str):
    """
    Queries the database for all context data for the target date AND SPORT,
    and merges it into a single canonical JSON payload grouped by game_id.

    Args:
        target_date: The date to check for context (YYYY-MM-DD).
        sport: The sport to filter the context by (e.g., 'NFL').

    Returns:
        A list of dictionaries, one for each game, ready for the LLM prompt.
    """
    # CRITICAL CHANGE: Pass sport to filter the database query
    raw_context = fetch_context_by_date(target_date, sport)

    # Group data by game_id
    games_map = {}

    for row in raw_context:
        game_id = row['game_id']
        context_type = row['context_type']

        if game_id not in games_map:
            # Initialize with the canonical structure
            games_map[game_id] = {
                "game_id": game_id,
                "match_date": row['match_date'],
                # team_pick might be null if no initial odds match was found
                "teams": {"team_pick": row['team_pick']},
                "context": CANONICAL_CONTEXT_STRUCTURE.copy()
            }

        # Merge data into the correct context type slot
        # NOTE: For simplicity, this assumes the last/latest context_type entry is the desired one.
        # For ensemble_notes, you would merge list entries.

        if context_type in games_map[game_id]["context"]:
            # Handle aggregation if necessary, but for now, overwrite with the data payload
            games_map[game_id]["context"][context_type] = row['data']

    return list(games_map.values())


def create_super_prompt_payload(target_date: str, sport: str):
    """
    Builds the final JSON payload containing all games and merged context
    to be inserted into the main AI super-prompt template.

    Args:
        target_date: The date being analyzed.
        sport: The sport being analyzed (e.g., 'NFL').
    """
    # CRITICAL CHANGE: Pass sport through to the builder
    merged_games = build_merged_context(target_date, sport)

    payload = {
        "analysis_date": datetime.now().isoformat(),
        "games": merged_games
    }
    return payload
