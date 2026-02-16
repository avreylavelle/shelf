"""Service layer for do-not-recommend list operations and exclusivity rules."""

from app.repos import dnr as dnr_repo
from app.repos import manga as manga_repo
from app.repos import ratings as ratings_repo
from app.repos import reading_list as reading_list_repo


def _normalize(username):
    """Normalize values for consistent comparisons."""
    return (username or "").strip().lower()


def list_items(user_id, sort="chron"):
    """Return items for the current context."""
    return dnr_repo.list_by_user(_normalize(user_id), sort=sort)


def add_item(user_id, manga_id):
    """Add item to storage."""
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    resolved = manga_repo.resolve_manga_ref(manga_id)
    canonical_id = resolved.get("canonical_id") or manga_id
    mdex_id = resolved.get("mdex_id")
    mal_id = resolved.get("mal_id")
    dnr_repo.add(user_id, canonical_id, canonical_id=canonical_id, mdex_id=mdex_id, mal_id=mal_id)
    # Keep the title exclusive to DNR
    ratings_repo.delete_rating(user_id, canonical_id)
    reading_list_repo.remove(user_id, canonical_id, canonical_id=canonical_id, mdex_id=mdex_id)
    return None


def remove_item(user_id, manga_id):
    """Remove item from storage."""
    user_id = _normalize(user_id)
    if not manga_id:
        return "manga_id is required"
    resolved = manga_repo.resolve_manga_ref(manga_id)
    canonical_id = resolved.get("canonical_id") or manga_id
    mdex_id = resolved.get("mdex_id")
    dnr_repo.remove(user_id, canonical_id, canonical_id=canonical_id, mdex_id=mdex_id)
    return None


def list_manga_ids(user_id):
    """Return manga ids for the current context."""
    return dnr_repo.list_manga_ids_by_user(_normalize(user_id))
