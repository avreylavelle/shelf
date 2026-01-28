from app.repos import profile as profile_repo
from app.repos import users as users_repo


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
    profile_repo.clear_preferences(_normalize(username))


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
