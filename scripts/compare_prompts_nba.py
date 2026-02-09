#!/usr/bin/env python3
"""
Compare two prompt versions side-by-side for NBA picks.

Usage:
    python3 scripts/compare_prompts_nba.py

Metrics:
    - Response time (speed)
    - Average confidence (quality)
    - Pick details for manual win rate tracking
"""

import json
import os
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# Import model calling functions
from app.rage_picks import (  # noqa: E402  # noqa: E402
    fetch_historical_nba,
    fetch_odds,
)
from app.utils.context_builder import create_super_prompt_payload  # noqa: E402
from app.utils.kalshi_api import fetch_kalshi_consensus  # noqa: E402
from app.utils.scraper import run_scrapers  # noqa: E402


def generate_picks_with_prompt(prompt_path, context, model_config, debug=False):
    """Generate picks using a specific prompt file."""
    # Load prompt
    with open(prompt_path) as f:
        prompt_template = f.read()

    prompt = prompt_template.replace(
        "{context_json}", json.dumps(context, indent=2))

    # Calculate prompt size
    prompt_tokens = len(prompt.split())  # Rough estimate

    # Time the generation
    start_time = time.time()

    # Call model based on provider - with raw response capture
    raw_response = None
    try:
        if model_config['provider'] == 'anthropic':
            # Custom call to capture raw response
            from anthropic import Anthropic

            from app.auth import get_config
            ANTHROPIC_API_KEY = get_config("ANTHROPIC_API_KEY")
            client = Anthropic(api_key=ANTHROPIC_API_KEY)
            json_prompt = f"{prompt}\n\nIMPORTANT: Return ONLY valid JSON in this exact format: {{\"picks\": [...]}}"
            response = client.messages.create(
                model=model_config['name'],
                max_tokens=4096,
                messages=[{"role": "user", "content": json_prompt}]
            )
            raw_response = response.content[0].text

            # Parse response
            raw = raw_response
            if raw.strip().startswith("```"):
                lines = raw.strip().split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw = '\n'.join(lines)

            try:
                picks = json.loads(raw).get("picks", [])
            except Exception as e:
                if debug:
                    print(f"   ⚠️ JSON parse error: {e}")
                picks = []
        else:
            picks = []
    except Exception as e:
        print(f"   ❌ Error: {e}")
        picks = []

    end_time = time.time()
    response_time = end_time - start_time

    return picks, response_time, prompt_tokens, raw_response


def calculate_metrics(picks):
    """Calculate metrics from picks."""
    if not picks:
        return {
            'count': 0,
            'avg_confidence': 0,
            'confidence_distribution': {},
            'market_distribution': {}
        }

    confidences = [p.get('confidence', 0) for p in picks]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    # Confidence distribution
    conf_dist = {}
    for c in confidences:
        conf_dist[c] = conf_dist.get(c, 0) + 1

    # Market distribution
    market_dist = {}
    for p in picks:
        market = p.get('market', 'unknown')
        market_dist[market] = market_dist.get(market, 0) + 1

    return {
        'count': len(picks),
        'avg_confidence': round(avg_confidence, 2),
        'confidence_distribution': conf_dist,
        'market_distribution': market_dist
    }


def compare_prompts():
    """Run comparison test."""
    print("\n" + "="*80)
    print("PROMPT COMPARISON TEST - NBA")
    print("="*80)

    sport_key = "basketball_nba"
    sport_name = "NBA"
    now_utc = datetime.now(UTC)
    target_date = now_utc.strftime('%Y-%m-%d')

    print(f"\n📅 Target Date: {target_date}")

    # Step 1: Fetch data (shared for both prompts)
    print("\n📊 Fetching Data...")
    try:
        run_scrapers(target_date, sport_key)
        fetch_kalshi_consensus(sport_key, target_date)
        print("   ✅ Data Fetched")
    except Exception as e:
        print(f"   ⚠️ Warning: {e}")

    # Build context
    context_payload = create_super_prompt_payload(target_date, sport_key)
    num_games = len(context_payload.get('games', []))
    print(f"   ✅ Context Built ({num_games} Games)")

    if num_games == 0:
        print("\n❌ No games found. Exiting.")
        return

    # Fetch odds
    raw_odds = fetch_odds(sport_key)
    if not raw_odds:
        print("   ❌ No upcoming games with odds found")
        return

    # Filter odds by time window (24 hours)
    max_24h = now_utc + timedelta(hours=24)
    filtered_odds = []
    for game in raw_odds:
        try:
            game_time = datetime.fromisoformat(
                game['commence_time'].replace('Z', '+00:00'))
            if now_utc < game_time <= max_24h:
                filtered_odds.append(game)
        except (ValueError, KeyError):
            continue

    print(f"   ✅ {len(filtered_odds)} games in next 24 hours")

    if not filtered_odds:
        print("\n❌ No games in time window. Exiting.")
        return

    # Fetch historical data
    history_team = filtered_odds[0]['home_team'] if filtered_odds else None
    if history_team:
        history_data = fetch_historical_nba(history_team)
    else:
        history_data = []

    # Build context
    context = {
        "odds_count": len(filtered_odds),
        "sport": sport_name.upper(),
        "sample_odds": filtered_odds[:15],
        "history": history_data,
        "extra_context": context_payload
    }

    # Model configuration (use first available model)
    model_config = {'provider': 'anthropic',
                    'name': 'claude-sonnet-4-5-20250929'}

    # Prompt paths
    prompt_v1_path = Path(parent_dir) / "prompts" / "picks_prompt_v1.txt"
    prompt_v2_path = Path(parent_dir) / "prompts" / "picks_prompt.txt"

    print(
        f"\n🔬 Testing Model: {model_config['provider']}:{model_config['name']}")

    # Test V1 (Original)
    print("\n" + "-"*80)
    print("TEST 1: Original Prompt (picks_prompt_v1.txt)")
    print("-"*80)
    picks_v1, time_v1, tokens_v1, raw_v1 = generate_picks_with_prompt(
        prompt_v1_path, context, model_config, debug=True)
    metrics_v1 = calculate_metrics(picks_v1)

    print(f"\n📝 Prompt Size: ~{tokens_v1:,} words")
    print(f"⏱️  Response Time: {time_v1:.2f}s")
    print(f"📊 Picks Generated: {metrics_v1['count']}")
    print(f"⭐ Avg Confidence: {metrics_v1['avg_confidence']}")
    print(
        f"📈 Confidence Distribution: {metrics_v1['confidence_distribution']}")
    print(f"🎯 Market Distribution: {metrics_v1['market_distribution']}")

    if picks_v1:
        print("\n📋 Picks:")
        for i, pick in enumerate(picks_v1, 1):
            print(
                f"   {i}. {pick.get('pick')} ({pick.get('market')}) - {pick.get('confidence')}⭐ @ {pick.get('odds_american')}")
    else:
        print("\n📋 No picks generated")
        if raw_v1:
            print(f"   Raw response preview: {raw_v1[:200]}...")

    # Test V2 (Optimized)
    print("\n" + "-"*80)
    print("TEST 2: Optimized Prompt (picks_prompt.txt)")
    print("-"*80)
    picks_v2, time_v2, tokens_v2, raw_v2 = generate_picks_with_prompt(
        prompt_v2_path, context, model_config, debug=True)
    metrics_v2 = calculate_metrics(picks_v2)

    print(f"\n📝 Prompt Size: ~{tokens_v2:,} words")
    print(f"⏱️  Response Time: {time_v2:.2f}s")
    print(f"📊 Picks Generated: {metrics_v2['count']}")
    print(f"⭐ Avg Confidence: {metrics_v2['avg_confidence']}")
    print(
        f"📈 Confidence Distribution: {metrics_v2['confidence_distribution']}")
    print(f"🎯 Market Distribution: {metrics_v2['market_distribution']}")

    if picks_v2:
        print("\n📋 Picks:")
        for i, pick in enumerate(picks_v2, 1):
            print(
                f"   {i}. {pick.get('pick')} ({pick.get('market')}) - {pick.get('confidence')}⭐ @ {pick.get('odds_american')}")
    else:
        print("\n📋 No picks generated")
        if raw_v2:
            print(f"   Raw response preview: {raw_v2[:200]}...")

    # Comparison Summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)

    time_diff = time_v1 - time_v2
    time_pct = (time_diff / time_v1 * 100) if time_v1 > 0 else 0

    tokens_diff = tokens_v1 - tokens_v2
    tokens_pct = (tokens_diff / tokens_v1 * 100) if tokens_v1 > 0 else 0

    print("\n📝 PROMPT SIZE:")
    print(f"   V1 (Original): ~{tokens_v1:,} words")
    print(f"   V2 (Optimized): ~{tokens_v2:,} words")
    print(f"   Reduction: {tokens_diff:,} words ({tokens_pct:.1f}%)")

    print("\n⏱️  SPEED:")
    print(f"   V1 (Original): {time_v1:.2f}s")
    print(f"   V2 (Optimized): {time_v2:.2f}s")
    print(f"   Improvement: {time_diff:.2f}s ({time_pct:+.1f}%)")

    print("\n⭐ CONFIDENCE:")
    print(f"   V1 (Original): {metrics_v1['avg_confidence']}")
    print(f"   V2 (Optimized): {metrics_v2['avg_confidence']}")
    conf_diff = metrics_v2['avg_confidence'] - metrics_v1['avg_confidence']
    print(f"   Difference: {conf_diff:+.2f}")

    print("\n📊 PICK COUNT:")
    print(f"   V1 (Original): {metrics_v1['count']}")
    print(f"   V2 (Optimized): {metrics_v2['count']}")

    # Save results for tracking
    results = {
        'timestamp': datetime.now(UTC).isoformat(),
        'sport': sport_name,
        'num_games': num_games,
        'model': f"{model_config['provider']}:{model_config['name']}",
        'v1': {
            'prompt_size_words': tokens_v1,
            'response_time': time_v1,
            'metrics': metrics_v1,
            'picks': picks_v1
        },
        'v2': {
            'prompt_size_words': tokens_v2,
            'response_time': time_v2,
            'metrics': metrics_v2,
            'picks': picks_v2
        },
        'improvements': {
            'prompt_size_reduction_pct': round(tokens_pct, 1),
            'speed_improvement_pct': round(time_pct, 1),
            'confidence_diff': round(conf_diff, 2)
        }
    }

    # Save to file
    results_dir = Path(parent_dir) / "test_results"
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / \
        f"prompt_comparison_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"

    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")
    print("\n📝 Track these picks to measure win rate over time!")


if __name__ == "__main__":
    compare_prompts()
