"""Shared Flask database connection helpers for per-request SQLite access."""

import sqlite3
from flask import current_app, g


def get_db():
    """Return db."""
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        g.db = db
    return g.db


def close_db(_error=None):
    """Handle close db for this module."""
    db = g.pop("db", None)
    if db is not None:
        db.close()
