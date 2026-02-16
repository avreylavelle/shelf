"""Reading-list service logic for add/remove/status updates."""

from app.repos import reading_list as reading_list_repo
from app.repos import manga as manga_repo
from app.repos import ratings as ratings_repo
from app.repos import dnr as dnr_repo


def _normalize(username):
    """Normalize values for consistent comparisons."""
    return (username or "").strip().lower()


def list_items(user_id, sort="chron"):
    """Return items for the current context."""
    return reading_list_repo.list_by_user(_normalize(user_id), sort=sort)


def add_item(user_id, manga_id, status="Plan to Read"):
    """Add item to storage."""
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    resolved = manga_repo.resolve_manga_ref(manga_id)
    canonical_id = resolved.get("canonical_id") or manga_id
    mdex_id = resolved.get("mdex_id")
    mal_id = resolved.get("mal_id")
    reading_list_repo.add(
        user_id,
        canonical_id,
        status,
        canonical_id=canonical_id,
        mdex_id=mdex_id,
        mal_id=mal_id,
    )
    # Keep the title exclusive to Reading List
    ratings_repo.delete_rating(user_id, canonical_id)
    dnr_repo.remove(user_id, canonical_id, canonical_id=canonical_id, mdex_id=mdex_id)
    return None


def remove_item(user_id, manga_id):
    """Remove item from storage."""
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    resolved = manga_repo.resolve_manga_ref(manga_id)
    canonical_id = resolved.get("canonical_id") or manga_id
    mdex_id = resolved.get("mdex_id")
    reading_list_repo.remove(user_id, canonical_id, canonical_id=canonical_id, mdex_id=mdex_id)
    return None


def list_manga_ids(user_id):
    """Return manga ids for the current context."""
    return reading_list_repo.list_manga_ids_by_user(_normalize(user_id))


def update_status(user_id, manga_id, status):
    """Update status with new values."""
    if not manga_id:
        return "manga_id is required"
    allowed = {"Plan to Read", "In Progress"}
    if status not in allowed:
        return "invalid status"
    resolved = manga_repo.resolve_manga_ref(manga_id)
    canonical_id = resolved.get("canonical_id") or manga_id
    mdex_id = resolved.get("mdex_id")
    mal_id = resolved.get("mal_id")
    reading_list_repo.update_status(_normalize(user_id), canonical_id, status, canonical_id=canonical_id, mdex_id=mdex_id, mal_id=mal_id)
    return None
