def decimal_to_american(decimal_odds: float) -> int:
    """
    Convert decimal odds to American odds.
    Example:
      2.10 -> +110
      1.91 -> -110
    """
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1) * 100))
    else:
        return int(round(-100 / (decimal_odds - 1)))


def american_to_probability(odds_american: int) -> float:
    """Convert American odds to implied probability (0–1)."""
    if odds_american is None:
        return None
    if odds_american > 0:
        return 100 / (odds_american + 100)
    else:
        return abs(odds_american) / (abs(odds_american) + 100)
