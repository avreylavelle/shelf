"""Data-access helpers for user account rows."""

from app.db import get_db


# User repository: credential row reads/writes in the users table.
def get_by_username(username):
    # Case-insensitive fetch so login normalization is resilient.
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,))
    return cur.fetchone()


def create_user(username, password_hash, age=None, gender=None, language="English", ui_prefs="{}"):
    # Normalize username and initialize serialized profile fields.
    username = (username or "").strip().lower()
    db = get_db()
    db.execute(
        """
        INSERT INTO users (username, age, gender, language, ui_prefs, preferred_genres, preferred_themes, blacklist_genres, blacklist_themes, signal_genres, signal_themes, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        # Initialize map-like columns as "{}" so parse helpers return dicts consistently.
        (username, age, gender, language, ui_prefs, "{}", "{}", "{}", "{}", "{}", "{}", password_hash),
    )
    db.commit()


def set_password_hash(username, password_hash):
    # Update stored password hash for existing user.
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE lower(username) = lower(?)", (password_hash, username))
    db.commit()


def delete_user(username):
    # Remove user identity row (related content cleanup is handled elsewhere).
    db = get_db()
    db.execute("DELETE FROM users WHERE lower(username) = lower(?)", (username,))
    db.commit()
