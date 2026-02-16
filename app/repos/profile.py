"""Data-access helpers for user profile and preference persistence."""

from app.db import get_db
from utils.parsing import parse_dict


# Profile repository: persists user profile fields and serialized preference maps.
def _coerce_counts(value):
    # Older rows may store list-like values; convert to count-map shape.
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        return {item: 1 for item in value}
    return {}


def get_profile(username):
    # Read and normalize profile payload for service/API layers.
    db = get_db()
    cur = db.execute(
        "SELECT username, age, gender, language, ui_prefs, preferred_genres, preferred_themes, signal_genres, signal_themes, blacklist_genres, blacklist_themes FROM users WHERE lower(username) = lower(?)",
        (username,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    # `parse_dict` handles legacy stringified dicts and empty/null values.
    blacklist_genres = _coerce_counts(parse_dict(row["blacklist_genres"]))
    blacklist_themes = _coerce_counts(parse_dict(row["blacklist_themes"]))
    return {
        "username": row["username"],
        "age": None if row["age"] is None else int(row["age"]),
        "gender": row["gender"] or "",
        "language": row["language"] or "English",
        "ui_prefs": parse_dict(row["ui_prefs"]),
        "preferred_genres": parse_dict(row["preferred_genres"]),
        "preferred_themes": parse_dict(row["preferred_themes"]),
        "signal_genres": parse_dict(row["signal_genres"]),
        "signal_themes": parse_dict(row["signal_themes"]),
        "blacklist_genres": blacklist_genres,
        "blacklist_themes": blacklist_themes,
    }


def update_profile(username, age=None, gender=None, language=None):
    # Persist editable basic profile fields.
    db = get_db()
    db.execute(
        "UPDATE users SET age = ?, gender = ?, language = ? WHERE lower(username) = lower(?)",
        (age, gender, language, username),
    )
    db.commit()


def update_username(old_username, new_username):
    # Keep user-owned rows connected when username changes.
    db = get_db()
    db.execute(
        "UPDATE users SET username = ? WHERE lower(username) = lower(?)",
        (new_username, old_username),
    )
    # Update ownership across core user-content tables.
    db.execute(
        "UPDATE user_ratings SET user_id = ? WHERE lower(user_id) = lower(?)",
        (new_username, old_username),
    )
    db.execute(
        "UPDATE user_dnr SET user_id = ? WHERE lower(user_id) = lower(?)",
        (new_username, old_username),
    )
    db.execute(
        "UPDATE user_reading_list SET user_id = ? WHERE lower(user_id) = lower(?)",
        (new_username, old_username),
    )
    # Note: event/request history tables are handled at service level if needed.
    db.commit()


def set_preferences(username, preferred_genres, preferred_themes):
    # Store rolling preference counts from request history.
    db = get_db()
    db.execute(
        "UPDATE users SET preferred_genres = ?, preferred_themes = ? WHERE lower(username) = lower(?)",
        # Values are stored as Python-literal strings for compatibility with `parse_dict`.
        (str(preferred_genres), str(preferred_themes), username),
    )
    db.commit()


def clear_preferences(username):
    # Convenience reset for preference maps.
    set_preferences(username, {}, {})


def clear_history(username):
    # Clear accumulated preference + blacklist history.
    db = get_db()
    db.execute(
        "UPDATE users SET preferred_genres = ?, preferred_themes = ?, blacklist_genres = ?, blacklist_themes = ? WHERE lower(username) = lower(?)",
        ("{}", "{}", "{}", "{}", username),
    )
    db.commit()


def set_ui_prefs(username, ui_prefs):
    # Persist UI flags/toggles as a serialized mapping.
    db = get_db()
    db.execute("UPDATE users SET ui_prefs = ? WHERE lower(username) = lower(?)", (str(ui_prefs), username))
    db.commit()


def set_signal_affinities(username, signal_genres, signal_themes):
    # Persist normalized implicit-signal affinity vectors.
    db = get_db()
    db.execute(
        "UPDATE users SET signal_genres = ?, signal_themes = ? WHERE lower(username) = lower(?)",
        (str(signal_genres), str(signal_themes), username),
    )
    db.commit()


def set_blacklist_history(username, blacklist_genres, blacklist_themes):
    # Persist rolling blacklist selections as count maps.
    db = get_db()
    db.execute(
        "UPDATE users SET blacklist_genres = ?, blacklist_themes = ? WHERE lower(username) = lower(?)",
        (str(blacklist_genres), str(blacklist_themes), username),
    )
    db.commit()
