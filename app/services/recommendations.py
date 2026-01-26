from data.get_repo import get_repo
from services.recommendations import get_recommendations as core_get_recommendations
from utils.lookup import get_all_unique

_OPTIONS_CACHE = None


def _load_options():
    manga_df = get_repo().get_manga_dataset()
    genres = get_all_unique(manga_df, "genres")
    themes = get_all_unique(manga_df, "themes")
    return genres, themes


def get_available_options(_db_path=None):
    global _OPTIONS_CACHE
    if _OPTIONS_CACHE is None:
        _OPTIONS_CACHE = _load_options()
    return _OPTIONS_CACHE


def recommend_for_user(_db_path, user_id, current_genres, current_themes, limit=20, update_profile=True):
    ranked, used_current = core_get_recommendations(
        user_id, current_genres, current_themes, k=limit
    )

    if ranked is None or ranked.empty:
        return [], used_current

    results = []
    for _, row in ranked.iterrows():
        results.append(
            {
                "id": row.get("id"),
                "title": row.get("title_name"),
                "score": row.get("score"),
                "genres": row.get("genres"),
                "themes": row.get("themes"),
                "match_score": row.get("match_score"),
                "internal_score": row.get("internal_score"),
                "combined_score": row.get("combined_score"),
            }
        )

    return results, used_current
