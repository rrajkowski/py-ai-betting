from datetime import datetime, timezone, timedelta
from app.utils.db import fetch_context_by_date  # Assumed to take (date, sport)
from app.utils.team_mapper import enrich_game_with_rankings

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
    Optimized with 3-day filtering and better logging.

    Args:
        target_date: The date to check for context (YYYY-MM-DD).
        sport: The sport to filter the context by (e.g., 'NFL', 'NCAAB').

    Returns:
        A list of dictionaries, one for each game, ready for the LLM prompt.
    """
    # Fetch all context from database
    raw_context = fetch_context_by_date(target_date, sport)

    print(
        f"🔍 Context Builder: Found {len(raw_context)} raw context records for {sport} on {target_date}")

    if not raw_context:
        print(
            f"⚠️ Context Builder: No context data found for {sport}. Check if scrapers/API ran successfully.")
        return []

    # Group data by game_id
    games_map = {}
    now_utc = datetime.now(timezone.utc)
    max_future_date = now_utc + timedelta(days=3)

    skipped_count = 0

    for row in raw_context:
        game_id = row['game_id']
        context_type = row['context_type']
        match_date_str = row.get('match_date')

        # Filter out games outside 3-day window
        if match_date_str:
            try:
                # Handle both full ISO timestamps and date-only strings
                # Date-only strings (e.g., "2025-12-15") should be treated as end-of-day
                # to avoid filtering out picks from scrapers that don't have exact game times
                if 'T' in match_date_str:
                    # Full ISO timestamp
                    match_dt = datetime.fromisoformat(
                        match_date_str.replace("Z", "+00:00"))
                else:
                    # Date-only string - treat as end of day (23:59:59 UTC)
                    match_dt = datetime.strptime(match_date_str, '%Y-%m-%d')
                    match_dt = match_dt.replace(
                        hour=23, minute=59, second=59, tzinfo=timezone.utc)

                if match_dt.tzinfo is None:
                    match_dt = match_dt.replace(tzinfo=timezone.utc)

                # Skip past games or games too far in future
                if match_dt < now_utc or match_dt > max_future_date:
                    skipped_count += 1
                    continue
            except Exception as e:
                print(
                    f"⚠️ Context Builder: Invalid date format for {game_id}: {match_date_str} ({e})")
                continue

        if game_id not in games_map:
            # Initialize with the canonical structure
            games_map[game_id] = {
                "game_id": game_id,
                "match_date": row['match_date'],
                # team_pick might be null if no initial odds match was found
                "teams": {"team_pick": row.get('team_pick')},
                "context": {
                    "expert_consensus": [],  # Changed to list to aggregate multiple sources
                    "public_consensus": {},
                    "neutral_site": {},
                    "coaching_factors": {},
                    "ensemble_notes": {},
                    "confidence_calibration": {}
                }
            }

        # Map context types to canonical structure
        # Expert picks from multiple sources should be aggregated
        source = row.get('source', 'unknown')
        data = row.get('data', {})

        if context_type in ['oddsshark_pick', 'oddstrader_pick', 'cbs_expert_pick', 'boydsbets_pick', 'expert_consensus']:
            # Add source attribution to the data
            data_with_source = data.copy() if isinstance(data, dict) else {}
            data_with_source['source'] = source
            games_map[game_id]["context"]["expert_consensus"].append(
                data_with_source)
        elif context_type == 'public_consensus':
            # Kalshi data - store as single object
            games_map[game_id]["context"]["public_consensus"] = data
        elif context_type in games_map[game_id]["context"]:
            # Other context types - store directly
            games_map[game_id]["context"][context_type] = data

    games_list = list(games_map.values())

    # Enrich games with ranking data for NCAAB and NCAAF
    if sport.upper() in ['NCAAB', 'NCAAF']:
        print(
            f"🏆 Context Builder: Enriching {len(games_list)} games with {sport} rankings...")
        for game in games_list:
            game_id = game.get('game_id', '')
            if game_id:
                ranking_info = enrich_game_with_rankings(game_id, sport)
                if 'error' not in ranking_info:
                    game['ranking_info'] = ranking_info

                    # Add summary to context for easy AI access
                    matchup = ranking_info.get('matchup_quality', {})
                    if matchup.get('matchup_type') != 'unranked':
                        game['context']['ranking_summary'] = {
                            'matchup_type': matchup.get('matchup_type'),
                            'quality_score': matchup.get('quality_score'),
                            'away_rank': matchup.get('away_rank'),
                            'home_rank': matchup.get('home_rank'),
                            'rank_differential': matchup.get('rank_differential')
                        }

    print(
        f"✅ Context Builder: Built context for {len(games_list)} games ({skipped_count} filtered out)")

    return games_list


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
