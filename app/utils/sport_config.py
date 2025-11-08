"""
Sport Configuration Module
Centralized configuration for sport seasons, schedules, and API limits.
Optimizes API calls based on actual game schedules and seasonal availability.
"""
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple


class SportConfig:
    """Configuration for sport-specific settings including seasons and game schedules."""

    # Season date ranges (month, day) - inclusive
    SEASONS = {
        "americanfootball_nfl": {
            "start": (9, 1),      # September 1
            "end": (2, 15),       # February 15 (includes playoffs/Super Bowl)
            "name": "NFL",
            "emoji": "🏈"
        },
        "americanfootball_ncaaf": {
            "start": (8, 20),     # August 20
            "end": (1, 15),       # January 15 (includes bowl games)
            "name": "NCAAF",
            "emoji": "🎓"
        },
        "basketball_ncaab": {
            "start": (11, 1),     # November 1
            "end": (4, 10),       # April 10 (includes March Madness)
            "name": "NCAAB",
            "emoji": "🏀"
        },
        "basketball_nba": {
            "start": (10, 15),    # October 15
            "end": (6, 20),       # June 20 (includes playoffs)
            "name": "NBA",
            "emoji": "🏀🏆"
        },
        "baseball_mlb": {
            "start": (3, 20),     # March 20
            "end": (11, 5),       # November 5 (includes World Series)
            "name": "MLB",
            "emoji": "⚾"
        }
    }

    # Kalshi API configuration
    KALSHI_CONFIG = {
        "americanfootball_nfl": {
            "ticker": "KXNFLGAME",
            "base_limit": 16,
            "schedule": {
                "thursday": 1,    # Thursday Night Football
                "sunday": 14,     # Sunday games (early + late)
                "monday": 1,      # Monday Night Football
                "default": 3      # Off-peak days
            }
        },
        "americanfootball_ncaaf": {
            "ticker": "KXNCAAFGAME",
            "base_limit": 50,
            "schedule": {
                "tuesday": 2,     # MACtion
                "wednesday": 2,   # MACtion
                "thursday": 5,    # Thursday games
                "friday": 8,      # Friday games
                "saturday": 40,   # Main game day
                "default": 5
            }
        },
        "basketball_ncaab": {
            "ticker": "KXNCAABGAME",
            "base_limit": 50,
            "schedule": {
                "tuesday": 40,    # Big game day
                "wednesday": 40,  # Big game day
                "thursday": 30,   # Many games
                "friday": 20,     # Moderate games
                "saturday": 50,   # Peak game day
                "sunday": 15,     # Fewer games
                "monday": 20,     # Moderate games
                "default": 20
            }
        },
        "basketball_nba": {
            "ticker": "KXNBAGAME",
            "base_limit": 12,
            "schedule": {
                "tuesday": 10,
                "wednesday": 10,
                "thursday": 8,
                "friday": 8,
                "saturday": 12,
                "sunday": 8,
                "monday": 6,
                "default": 8
            }
        },
        "baseball_mlb": {
            "ticker": "KXMLBGAME",
            "base_limit": 15,
            "schedule": {
                "default": 15     # Games almost every day
            }
        }
    }

    # Historical data limits (games to fetch per team)
    HISTORICAL_LIMITS = {
        "americanfootball_nfl": 16,      # Full season context
        # Recent season context (reduced from 30 for speed)
        "americanfootball_ncaaf": 12,
        # Last ~2 weeks of games (increased from 8)
        "basketball_ncaab": 10,
        "basketball_nba": 12,            # Last ~2 weeks of games
        "baseball_mlb": 10               # Last ~2 weeks of games
    }

    # Days to look back for historical scores
    HISTORICAL_DAYS = {
        "americanfootball_nfl": 120,     # ~17 weeks
        "americanfootball_ncaaf": 100,   # ~14 weeks
        "basketball_ncaab": 30,          # ~1 month
        "basketball_nba": 30,            # ~1 month
        "baseball_mlb": 30               # ~1 month
    }

    @classmethod
    def is_in_season(cls, sport_key: str, check_date: Optional[datetime] = None) -> bool:
        """
        Check if a sport is currently in season.

        Args:
            sport_key: Sport identifier (e.g., 'americanfootball_nfl')
            check_date: Date to check (defaults to now)

        Returns:
            True if sport is in season, False otherwise
        """
        if check_date is None:
            check_date = datetime.now(timezone.utc)

        season = cls.SEASONS.get(sport_key)
        if not season:
            return False

        start_month, start_day = season["start"]
        end_month, end_day = season["end"]

        current_month = check_date.month
        current_day = check_date.day

        # Handle seasons that span year boundary (e.g., NFL: Sep-Feb)
        if start_month > end_month:
            # Season crosses New Year
            in_season = (
                (current_month > start_month) or
                (current_month == start_month and current_day >= start_day) or
                (current_month < end_month) or
                (current_month == end_month and current_day <= end_day)
            )
        else:
            # Season within same calendar year
            in_season = (
                (current_month > start_month or (current_month == start_month and current_day >= start_day)) and
                (current_month < end_month or (
                    current_month == end_month and current_day <= end_day))
            )

        return in_season

    @classmethod
    def get_dynamic_limit(cls, sport_key: str, check_date: Optional[datetime] = None) -> int:
        """
        Get dynamic game limit based on day of week and season.

        Args:
            sport_key: Sport identifier
            check_date: Date to check (defaults to now)

        Returns:
            Optimal limit for API calls
        """
        if check_date is None:
            check_date = datetime.now(timezone.utc)

        # Return 0 if out of season
        if not cls.is_in_season(sport_key, check_date):
            return 0

        config = cls.KALSHI_CONFIG.get(sport_key)
        if not config:
            return 10  # Default fallback

        # Get day of week (0=Monday, 6=Sunday)
        day_name = check_date.strftime("%A").lower()

        schedule = config.get("schedule", {})
        return schedule.get(day_name, schedule.get("default", config["base_limit"]))

    @classmethod
    def get_kalshi_ticker(cls, sport_key: str) -> Optional[str]:
        """Get Kalshi ticker for a sport."""
        config = cls.KALSHI_CONFIG.get(sport_key)
        return config["ticker"] if config else None

    @classmethod
    def get_sport_name(cls, sport_key: str) -> str:
        """Get uppercase sport name from sport key (e.g., 'americanfootball_nfl' -> 'NFL')."""
        season_config = cls.SEASONS.get(sport_key, {})
        return season_config.get("name", sport_key.split("_")[-1].upper())

    @classmethod
    def get_historical_limit(cls, sport_key: str) -> int:
        """Get historical game limit for a sport."""
        return cls.HISTORICAL_LIMITS.get(sport_key, 10)

    @classmethod
    def get_historical_days(cls, sport_key: str) -> int:
        """Get days to look back for historical data."""
        return cls.HISTORICAL_DAYS.get(sport_key, 30)

    @classmethod
    def get_active_sports(cls, check_date: Optional[datetime] = None) -> list:
        """
        Get list of sports currently in season.

        Args:
            check_date: Date to check (defaults to now)

        Returns:
            List of sport keys that are in season
        """
        if check_date is None:
            check_date = datetime.now(timezone.utc)

        active = []
        for sport_key in cls.SEASONS.keys():
            if cls.is_in_season(sport_key, check_date):
                active.append(sport_key)

        return active

    @classmethod
    def get_sport_info(cls, sport_key: str) -> Dict:
        """Get all configuration info for a sport."""
        season = cls.SEASONS.get(sport_key, {})
        kalshi = cls.KALSHI_CONFIG.get(sport_key, {})

        return {
            "sport_key": sport_key,
            "name": season.get("name", sport_key.upper()),
            "emoji": season.get("emoji", "🏆"),
            "in_season": cls.is_in_season(sport_key),
            "kalshi_ticker": kalshi.get("ticker"),
            "dynamic_limit": cls.get_dynamic_limit(sport_key),
            "historical_limit": cls.get_historical_limit(sport_key),
            "historical_days": cls.get_historical_days(sport_key)
        }
