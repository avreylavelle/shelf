from app.repos import reading_list as reading_list_repo
from app.repos import ratings as ratings_repo
from app.repos import dnr as dnr_repo


def _normalize(username):
    return (username or "").strip().lower()


def list_items(user_id, sort="chron"):
    return reading_list_repo.list_by_user(_normalize(user_id), sort=sort)


def add_item(user_id, manga_id, status="Plan to Read"):
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    reading_list_repo.add(user_id, manga_id, status)
    # Keep the title exclusive to Reading List
    ratings_repo.delete_rating(user_id, manga_id)
    dnr_repo.remove(user_id, manga_id)
    return None


def remove_item(user_id, manga_id):
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    reading_list_repo.remove(user_id, manga_id)
    return None


def list_manga_ids(user_id):
    return reading_list_repo.list_manga_ids_by_user(_normalize(user_id))


def update_status(user_id, manga_id, status):
    if not manga_id:
        return "manga_id is required"
    allowed = {"Plan to Read", "In Progress"}
    if status not in allowed:
        return "invalid status"
    reading_list_repo.update_status(_normalize(user_id), manga_id, status)
    return None
