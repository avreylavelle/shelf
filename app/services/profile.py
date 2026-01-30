import json

from app.db import get_db
from app.repos import profile as profile_repo
from app.repos import users as users_repo
from utils.parsing import parse_dict, parse_list


def _normalize(username):
    return (username or "").strip().lower()


def get_profile(username):
    return profile_repo.get_profile(_normalize(username))


def update_profile(username, age=None, gender=None, language=None):
    profile_repo.update_profile(_normalize(username), age=age, gender=gender, language=language)


def change_username(old_username, new_username):
    new_username = _normalize(new_username)
    old_username = _normalize(old_username)
    if not new_username:
        return "username is required"
    if old_username == new_username:
        return None

    existing = users_repo.get_by_username(new_username)
    if existing and existing["username"].lower() != old_username:
        return "Username already exists"

    # Update both users table + ratings ownership
    profile_repo.update_username(old_username, new_username)
    return None


def clear_history(username):
    username = _normalize(username)
    profile_repo.clear_history(username)
    db = get_db()
    db.execute("DELETE FROM user_requests WHERE lower(user_id) = lower(?)", (username,))
    db.execute("DELETE FROM user_request_cache WHERE lower(user_id) = lower(?)", (username,))
    db.commit()


def increment_preferences(username, current_genres, current_themes):
    profile = profile_repo.get_profile(_normalize(username))
    if not profile:
        return

    preferred_genres = dict(profile.get("preferred_genres", {}))
    preferred_themes = dict(profile.get("preferred_themes", {}))

    # Add +1 to each selected option (this is the "memory")
    for genre in current_genres:
        preferred_genres[genre] = preferred_genres.get(genre, 0) + 1
    for theme in current_themes:
        preferred_themes[theme] = preferred_themes.get(theme, 0) + 1

    profile_repo.set_preferences(_normalize(username), preferred_genres, preferred_themes)


def set_ui_prefs(username, ui_prefs):
    profile_repo.set_ui_prefs(_normalize(username), ui_prefs)


def get_ui_prefs(username):
    profile = profile_repo.get_profile(_normalize(username))
    if not profile:
        return {}
    return profile.get("ui_prefs", {})


def set_signal_affinities(username, signal_genres, signal_themes):
    profile_repo.set_signal_affinities(_normalize(username), signal_genres, signal_themes)


def increment_blacklist_history(username, blacklist_genres, blacklist_themes):
    profile = profile_repo.get_profile(_normalize(username))
    if not profile:
        return

    blacklist_genres = blacklist_genres or []
    blacklist_themes = blacklist_themes or []
    if not blacklist_genres and not blacklist_themes:
        return

    genre_history = dict(profile.get("blacklist_genres", {}))
    theme_history = dict(profile.get("blacklist_themes", {}))

    for genre in blacklist_genres:
        genre_history[genre] = genre_history.get(genre, 0) + 1
    for theme in blacklist_themes:
        theme_history[theme] = theme_history.get(theme, 0) + 1

    profile_repo.set_blacklist_history(_normalize(username), genre_history, theme_history)


def record_request_history(username, current_genres, current_themes, blacklist_genres, blacklist_themes, max_requests=100):
    username = _normalize(username)
    db = get_db()

    current_genres = [g for g in (current_genres or []) if g]
    current_themes = [t for t in (current_themes or []) if t]
    blacklist_genres = [g for g in (blacklist_genres or []) if g]
    blacklist_themes = [t for t in (blacklist_themes or []) if t]

    db.execute(
        """
        INSERT INTO user_requests (user_id, genres, themes, blacklist_genres, blacklist_themes)
        VALUES (lower(?), ?, ?, ?, ?)
        """,
        (
            username,
            json.dumps(current_genres),
            json.dumps(current_themes),
            json.dumps(blacklist_genres),
            json.dumps(blacklist_themes),
        ),
    )

    row = db.execute(
        """
        SELECT request_count, preferred_genres, preferred_themes, blacklist_genres, blacklist_themes
        FROM user_request_cache
        WHERE lower(user_id) = lower(?)
        """,
        (username,),
    ).fetchone()

    preferred_genres = parse_dict(row["preferred_genres"]) if row else {}
    preferred_themes = parse_dict(row["preferred_themes"]) if row else {}
    blacklist_genre_counts = parse_dict(row["blacklist_genres"]) if row else {}
    blacklist_theme_counts = parse_dict(row["blacklist_themes"]) if row else {}
    request_count = int(row["request_count"]) if row and row["request_count"] is not None else 0

    def apply_delta(target, items, delta):
        for item in items:
            if not item:
                continue
            target[item] = target.get(item, 0) + delta
            if target[item] <= 0:
                del target[item]

    apply_delta(preferred_genres, current_genres, 1)
    apply_delta(preferred_themes, current_themes, 1)
    apply_delta(blacklist_genre_counts, blacklist_genres, 1)
    apply_delta(blacklist_theme_counts, blacklist_themes, 1)
    request_count += 1

    while request_count > max_requests:
        oldest = db.execute(
            """
            SELECT id, genres, themes, blacklist_genres, blacklist_themes
            FROM user_requests
            WHERE lower(user_id) = lower(?)
            ORDER BY created_at ASC, id ASC
            LIMIT 1
            """,
            (username,),
        ).fetchone()
        if not oldest:
            break
        apply_delta(preferred_genres, parse_list(oldest["genres"]), -1)
        apply_delta(preferred_themes, parse_list(oldest["themes"]), -1)
        apply_delta(blacklist_genre_counts, parse_list(oldest["blacklist_genres"]), -1)
        apply_delta(blacklist_theme_counts, parse_list(oldest["blacklist_themes"]), -1)
        db.execute("DELETE FROM user_requests WHERE id = ?", (oldest["id"],))
        request_count -= 1

    db.execute(
        """
        INSERT INTO user_request_cache (
            user_id, request_count, preferred_genres, preferred_themes, blacklist_genres, blacklist_themes, updated_at
        )
        VALUES (lower(?), ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            request_count = excluded.request_count,
            preferred_genres = excluded.preferred_genres,
            preferred_themes = excluded.preferred_themes,
            blacklist_genres = excluded.blacklist_genres,
            blacklist_themes = excluded.blacklist_themes,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            username,
            request_count,
            str(preferred_genres),
            str(preferred_themes),
            str(blacklist_genre_counts),
            str(blacklist_theme_counts),
        ),
    )

    db.execute(
        """
        UPDATE users
        SET preferred_genres = ?, preferred_themes = ?, blacklist_genres = ?, blacklist_themes = ?
        WHERE lower(username) = lower(?)
        """,
        (
            str(preferred_genres),
            str(preferred_themes),
            str(blacklist_genre_counts),
            str(blacklist_theme_counts),
            username,
        ),
    )
    db.commit()
