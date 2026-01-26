from app.repos import ratings as ratings_repo


def list_ratings(user_id, sort="chron"):
    return ratings_repo.list_by_user(user_id, sort=sort)


def list_ratings_map(user_id):
    return ratings_repo.list_ratings_map(user_id)


def set_rating(user_id, manga_id, rating):
    if not manga_id:
        return "manga_id is required"

    if rating is not None:
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            return "rating must be a number"
        if rating < 0 or rating > 10:
            return "rating must be between 0 and 10"

    ratings_repo.upsert_rating(user_id, manga_id, rating)
    return None


def delete_rating(user_id, manga_id):
    if not manga_id:
        return "manga_id is required"
    ratings_repo.delete_rating(user_id, manga_id)
    return None
