"""Shared pytest fixtures for the test suite."""

import os
import tempfile

import pytest


@pytest.fixture()
def tmp_db(monkeypatch, tmp_path):
    """
    Provide a temporary SQLite database for tests that touch the DB.

    Monkeypatches app.db.DB_PATH so every call to get_db() uses
    the ephemeral file instead of the real database.
    """
    db_file = str(tmp_path / "test_bets.db")
    monkeypatch.setattr("app.db.DB_PATH", db_file)

    # Also patch BACKUP_DIR so backup tests don't touch real backups
    backup_dir = str(tmp_path / "backups")
    monkeypatch.setattr("app.db.BACKUP_DIR", backup_dir)

    # Initialise tables
    from app.db import init_ai_picks, init_db, init_prompt_context_db

    init_db()
    init_ai_picks()
    init_prompt_context_db()

    return db_file

