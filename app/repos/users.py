"""Data-access helpers for user account rows."""

from app.db import get_db


# User repository: credential row reads/writes in the users table.
def get_by_username(username):
    # Case-insensitive fetch so login normalization is resilient.
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,))
    return cur.fetchone()


def is_admin(username):
    # Role checks are sourced from DB instead of hardcoded usernames.
    user = get_by_username(username)
    if not user:
        return False
    try:
        return bool(user["is_admin"])
    except Exception:
        return False


def has_any_admin():
    # Used for first-admin bootstrap gating.
    db = get_db()
    row = db.execute("SELECT 1 FROM users WHERE COALESCE(is_admin, 0) = 1 LIMIT 1").fetchone()
    return bool(row)


def create_user(username, password_hash, age=None, gender=None, language="English", ui_prefs="{}", is_admin=0):
    # Normalize username and initialize serialized profile fields.
    username = (username or "").strip().lower()
    db = get_db()
    db.execute(
        """
        INSERT INTO users (username, age, gender, language, ui_prefs, preferred_genres, preferred_themes, blacklist_genres, blacklist_themes, signal_genres, signal_themes, password_hash, is_admin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        # Initialize map-like columns as "{}" so parse helpers return dicts consistently.
        (username, age, gender, language, ui_prefs, "{}", "{}", "{}", "{}", "{}", "{}", password_hash, 1 if is_admin else 0),
    )
    db.commit()


def set_password_hash(username, password_hash):
    # Update stored password hash for existing user.
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE lower(username) = lower(?)", (password_hash, username))
    db.commit()


def set_admin(username, is_admin_flag=True):
    # Explicit role assignment for admin bootstrap and management operations.
    db = get_db()
    db.execute(
        "UPDATE users SET is_admin = ? WHERE lower(username) = lower(?)",
        (1 if is_admin_flag else 0, username),
    )
    db.commit()


def delete_user(username):
    # Explicit delete policy: full cascade cleanup across all user-owned tables.
    db = get_db()
    db.execute("DELETE FROM user_ratings WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM user_dnr WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM user_reading_list WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM user_events WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM user_requests WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM user_request_cache WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM users WHERE lower(username) = lower(?)", (username,))
    db.commit()
