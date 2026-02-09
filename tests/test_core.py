"""
Pytest tests for core grading, picks, and utility functions.

Covers:
  - _check_pick_result  (grading logic)
  - normalize_pick_team
  - is_conflicting_pick
  - validate_pick_against_consensus
  - _safe_parse_datetime
  - get_db context manager
  - backup_db / _prune_old_backups
"""

import os

import pytest

from app.db import _prune_old_backups, backup_db, get_db
from app.grading import _check_pick_result
from app.picks import is_conflicting_pick, normalize_pick_team, validate_pick_against_consensus
from app.rage_picks import _safe_parse_datetime


# ---------------------------------------------------------------------------
# _check_pick_result — H2H / Spreads / Totals
# ---------------------------------------------------------------------------


class TestCheckPickResultH2H:
    """H2H (moneyline) grading."""

    def _pick(self, game, pick_team):
        return {"game": game, "pick": pick_team, "market": "h2h", "line": None}

    def test_away_win(self):
        assert _check_pick_result(
            self._pick("Ottawa Senators @ Montréal Canadiens",
                       "Ottawa Senators"),
            home_score=3, away_score=5,
        ) == "Win"

    def test_home_loss(self):
        assert _check_pick_result(
            self._pick("Ottawa Senators @ Montréal Canadiens",
                       "Montréal Canadiens"),
            home_score=3, away_score=5,
        ) == "Loss"

    def test_tie_is_push(self):
        assert _check_pick_result(
            self._pick("Ottawa Senators @ Montréal Canadiens",
                       "Ottawa Senators"),
            home_score=3, away_score=3,
        ) == "Push"

    def test_no_at_symbol_returns_pending(self):
        assert _check_pick_result(
            self._pick("Team A vs Team B", "Team A"),
            home_score=3, away_score=5,
        ) == "Pending"

    def test_none_scores_returns_pending(self):
        assert _check_pick_result(
            self._pick("A @ B", "A"), home_score=None, away_score=5,
        ) == "Pending"


class TestCheckPickResultSpreads:
    """Spread grading."""

    def _pick(self, pick_team, line):
        return {
            "game": "Team A @ Team B",
            "pick": pick_team,
            "market": "spreads",
            "line": line,
        }

    def test_away_covers(self):
        # Away -1.5, wins by 2 → 5 + (-1.5) = 3.5 > 3 → Win
        assert _check_pick_result(self._pick(
            "Team A", -1.5), home_score=3, away_score=5) == "Win"

    def test_home_underdog_fails(self):
        # Home +1.5, loses by 2 → 3 + 1.5 = 4.5 < 5 → Loss
        assert _check_pick_result(self._pick(
            "Team B", 1.5), home_score=3, away_score=5) == "Loss"

    def test_push(self):
        # Away -2.0, wins by 2 → 5 + (-2) = 3 == 3 → Push
        assert _check_pick_result(self._pick(
            "Team A", -2.0), home_score=3, away_score=5) == "Push"

    def test_no_line_returns_pending(self):
        assert _check_pick_result(
            {"game": "A @ B", "pick": "A", "market": "spreads", "line": None},
            home_score=3, away_score=5,
        ) == "Pending"


class TestCheckPickResultTotals:
    """Totals (over/under) grading."""

    def _pick(self, direction, line):
        return {
            "game": "Team A @ Team B",
            "pick": direction,
            "market": "totals",
            "line": line,
        }

    def test_over_win(self):
        # Total 8, line 6.5 → Over wins
        assert _check_pick_result(self._pick(
            "Over", 6.5), home_score=3, away_score=5) == "Win"

    def test_under_loss(self):
        assert _check_pick_result(self._pick(
            "Under", 6.5), home_score=3, away_score=5) == "Loss"

    def test_under_push(self):
        # Total 8, line 8.0 → Push
        assert _check_pick_result(self._pick(
            "Under", 8.0), home_score=3, away_score=5) == "Push"

    def test_over_push(self):
        assert _check_pick_result(self._pick(
            "Over", 8.0), home_score=3, away_score=5) == "Push"

    def test_no_line_returns_pending(self):
        assert _check_pick_result(self._pick(
            "Over", None), home_score=3, away_score=5) == "Pending"


# ---------------------------------------------------------------------------
# normalize_pick_team
# ---------------------------------------------------------------------------


class TestNormalizePickTeam:
    def test_strips_positive_line(self):
        assert normalize_pick_team(
            "Tulane Green Wave +17.5", 17.5) == "tulane green wave"

    def test_strips_negative_line(self):
        assert normalize_pick_team(
            "Ole Miss Rebels -3.5", -3.5) == "ole miss rebels"

    def test_no_line(self):
        assert normalize_pick_team("Boston Celtics", None) == "boston celtics"

    def test_whitespace(self):
        assert normalize_pick_team("  Miami Heat  ", None) == "miami heat"


# ---------------------------------------------------------------------------
# is_conflicting_pick
# ---------------------------------------------------------------------------


class TestIsConflictingPick:
    def test_h2h_different_team_conflicts(self):
        existing = [("Team A", None)]
        assert is_conflicting_pick(
            "A @ B", "h2h", "Team B", None, existing) is True

    def test_h2h_same_team_no_conflict(self):
        existing = [("Team A", None)]
        assert is_conflicting_pick(
            "A @ B", "h2h", "Team A", None, existing) is False

    def test_totals_over_under_conflicts(self):
        existing = [("Over", 210.5)]
        assert is_conflicting_pick(
            "A @ B", "totals", "Under", 210.5, existing) is True

    def test_totals_same_direction_no_conflict(self):
        existing = [("Over", 210.5)]
        assert is_conflicting_pick(
            "A @ B", "totals", "Over", 210.5, existing) is False

    def test_spread_opposite_signs_conflict(self):
        existing = [("Team A -3.5", -3.5)]
        assert is_conflicting_pick(
            "A @ B", "spreads", "Team B +3.5", 3.5, existing) is True

    def test_empty_existing_no_conflict(self):
        assert is_conflicting_pick("A @ B", "h2h", "Team A", None, []) is False


# ---------------------------------------------------------------------------
# validate_pick_against_consensus
# ---------------------------------------------------------------------------


class TestValidatePickAgainstConsensus:
    def _context(self, game_id, directions):
        """Build a minimal context payload with expert consensus."""
        experts = [{"direction": d} for d in directions]
        return {"games": [{"game_id": game_id, "context": {"expert_consensus": experts}}]}

    def test_matching_direction_valid(self):
        ctx = self._context("A @ B", ["over", "over", "under"])
        pick = {"game": "A @ B", "market": "totals", "pick": "Over"}
        is_valid, _ = validate_pick_against_consensus(pick, ctx)
        assert is_valid is True

    def test_opposing_direction_invalid(self):
        ctx = self._context("A @ B", ["over", "over", "under"])
        pick = {"game": "A @ B", "market": "totals", "pick": "Under"}
        is_valid, reason = validate_pick_against_consensus(pick, ctx)
        assert is_valid is False
        assert "consensus" in reason.lower()

    def test_split_consensus_valid(self):
        ctx = self._context("A @ B", ["over", "under"])
        pick = {"game": "A @ B", "market": "totals", "pick": "Over"}
        is_valid, reason = validate_pick_against_consensus(pick, ctx)
        assert is_valid is True
        assert "split" in reason.lower()

    def test_no_context_always_valid(self):
        pick = {"game": "A @ B", "market": "h2h", "pick": "Team A"}
        is_valid, _ = validate_pick_against_consensus(pick, {"games": []})
        assert is_valid is True

    def test_no_consensus_data_valid(self):
        ctx = {"games": [{"game_id": "A @ B",
                          "context": {"expert_consensus": []}}]}
        pick = {"game": "A @ B", "market": "totals", "pick": "Over"}
        is_valid, _ = validate_pick_against_consensus(pick, ctx)
        assert is_valid is True


# ---------------------------------------------------------------------------
# _safe_parse_datetime
# ---------------------------------------------------------------------------


class TestSafeParseDatetime:
    def test_iso_with_z(self):
        dt = _safe_parse_datetime("2026-02-09T12:00:00Z")
        assert dt is not None
        assert dt.year == 2026
        assert dt.month == 2

    def test_iso_with_offset(self):
        dt = _safe_parse_datetime("2026-02-09T12:00:00+00:00")
        assert dt is not None

    def test_none_input(self):
        assert _safe_parse_datetime(None) is None

    def test_empty_string(self):
        assert _safe_parse_datetime("") is None

    def test_null_string(self):
        assert _safe_parse_datetime("null") is None

    def test_nan_string(self):
        assert _safe_parse_datetime("nan") is None

    def test_garbage_input(self):
        assert _safe_parse_datetime("not-a-date") is None


# ---------------------------------------------------------------------------
# get_db context manager
# ---------------------------------------------------------------------------


class TestGetDb:
    def test_context_manager_returns_connection(self, tmp_db):
        with get_db() as conn:
            assert conn is not None
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [r[0] for r in cur.fetchall()]
            assert "bets" in tables
            assert "ai_picks" in tables

    def test_connection_closed_after_context(self, tmp_db):
        import sqlite3

        with get_db() as conn:
            pass
        # After context exits, conn should be closed
        with pytest.raises(Exception):
            conn.execute("SELECT 1")


# ---------------------------------------------------------------------------
# backup_db / _prune_old_backups
# ---------------------------------------------------------------------------


class TestBackupDb:
    def test_creates_backup_file(self, tmp_db, tmp_path):
        path = backup_db(tag="test")
        assert path is not None
        assert os.path.exists(path)
        assert "bets_test_" in os.path.basename(path)

    def test_returns_none_when_db_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("app.db.DB_PATH", str(tmp_path / "missing.db"))
        monkeypatch.setattr("app.db.BACKUP_DIR", str(tmp_path / "backups"))
        assert backup_db(tag="test") is None

    def test_prune_keeps_max_backups(self, tmp_db, tmp_path, monkeypatch):
        import time

        monkeypatch.setattr("app.db.MAX_BACKUPS", 3)
        backup_dir = str(tmp_path / "backups")
        monkeypatch.setattr("app.db.BACKUP_DIR", backup_dir)

        # Create 5 backups
        for i in range(5):
            backup_db(tag=f"prune{i}")
            time.sleep(0.05)  # Ensure distinct mtimes

        from pathlib import Path
        remaining = list(Path(backup_dir).glob("bets_*.db"))
        assert len(remaining) == 3
