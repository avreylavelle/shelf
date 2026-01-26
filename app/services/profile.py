from app.repos import profile as profile_repo
from app.repos import users as users_repo


def get_profile(username):
    return profile_repo.get_profile(username)


def update_profile(username, age=None, gender=None):
    profile_repo.update_profile(username, age=age, gender=gender)


def change_username(old_username, new_username):
    if not new_username:
        return "username is required"
    if old_username == new_username:
        return None

    existing = users_repo.get_by_username(new_username)
    if existing:
        return "Username already exists"

    profile_repo.update_username(old_username, new_username)
    return None


def clear_history(username):
    profile_repo.clear_preferences(username)


def increment_preferences(username, current_genres, current_themes):
    profile = profile_repo.get_profile(username)
    if not profile:
        return

    preferred_genres = dict(profile.get("preferred_genres", {}))
    preferred_themes = dict(profile.get("preferred_themes", {}))

    for genre in current_genres:
        preferred_genres[genre] = preferred_genres.get(genre, 0) + 1
    for theme in current_themes:
        preferred_themes[theme] = preferred_themes.get(theme, 0) + 1

    profile_repo.set_preferences(username, preferred_genres, preferred_themes)
