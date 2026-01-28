
from legacy.cli.data.get_repo import get_repo


def load_manga_dataset():
    return get_repo().get_manga_dataset()


def load_user_index():
    return get_repo().get_all_users()


def get_profile(user_df, username):
    return get_repo().get_user_by_username(username)


def similar_username(user_df, username, n=3, cutoff=0.7):
    existing = get_repo().get_all_users()["username"].dropna().astype(str).tolist()
    from difflib import get_close_matches

    return get_close_matches(username, existing, n=n, cutoff=cutoff)


def save_user_profile(user_df, profile):
    get_repo().create_user(
        username=profile["username"],
        age=profile.get("age", None),
        gender=profile.get("gender", ""),
        preferred_genres=profile.get("preferred_genres", {}),
        preferred_themes=profile.get("preferred_themes", {}),
    )
    return get_repo().get_all_users()


def search_manga(query, lang="en", limit=20):
    return get_repo().search_manga_titles(query, limit=limit, lang=lang)


def add_rating(user_id, manga_id, rating):
    return get_repo().upsert_rating(user_id, manga_id, rating)


def remove_rating(user_id, manga_id):
    return get_repo().delete_rating(user_id, manga_id)


def list_ratings(user_id):
    return get_repo().get_user_ratings(user_id)
