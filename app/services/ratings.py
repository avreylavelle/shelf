from app.repos import ratings as ratings_repo


def list_ratings(user_id, sort="chron"):
    return ratings_repo.list_by_user(user_id, sort=sort)


def list_ratings_map(user_id):
    return ratings_repo.list_ratings_map(user_id)


def set_rating(user_id, manga_id, rating, recommended_by_us=None):
    if not manga_id:
        return "manga_id is required"


    if recommended_by_us is None:
        recommended_by_us = 0
    else:
        recommended_by_us = 1 if bool(recommended_by_us) else 0
    if rating is not None:
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            return "rating must be a number"
        if rating < 0 or rating > 10:
            return "rating must be between 0 and 10"

    # Upsert keeps one rating per user/title
    ratings_repo.upsert_rating(user_id, manga_id, rating, recommended_by_us)
    return None


def delete_rating(user_id, manga_id):
    if not manga_id:
        return "manga_id is required"
    ratings_repo.delete_rating(user_id, manga_id)
    return None
