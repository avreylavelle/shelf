from app.repos import ratings as ratings_repo
from app.repos import dnr as dnr_repo
from app.repos import reading_list as reading_list_repo


def _normalize(username):
    return (username or "").strip().lower()


def list_ratings(user_id, sort="chron"):
    return ratings_repo.list_by_user(_normalize(user_id), sort=sort)


def list_ratings_map(user_id):
    return ratings_repo.list_ratings_map(_normalize(user_id))


def set_rating(user_id, manga_id, rating, recommended_by_us=None, finished_reading=None):
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"

    if recommended_by_us is None:
        recommended_by_us = 0
    else:
        recommended_by_us = 1 if bool(recommended_by_us) else 0

    if finished_reading is None:
        finished_reading = 0
    else:
        finished_reading = 1 if bool(finished_reading) else 0

    if rating is None:
        existing = ratings_repo.get_rating_value(user_id, manga_id)
        if existing is not None:
            rating = existing

    if rating is not None:
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            return "rating must be a number"
        if rating < 0 or rating > 10:
            return "rating must be between 0 and 10"

    # Upsert keeps one rating per user/title
    ratings_repo.upsert_rating(user_id, manga_id, rating, recommended_by_us, finished_reading)
    # Keep the title exclusive to ratings
    dnr_repo.remove(user_id, manga_id)
    reading_list_repo.remove(user_id, manga_id)
    return None


def delete_rating(user_id, manga_id):
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    ratings_repo.delete_rating(user_id, manga_id)
    return None
