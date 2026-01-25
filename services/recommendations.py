from core.recommendations import score_recommendations
from data.get_repo import get_repo


def get_recommendations(user_id, current_genres, current_themes, k=20, lang="en"):
    repo = get_repo()
    manga_df = repo.get_manga_dataset()
    profile = repo.get_user_by_username(user_id)
    if profile is None:
        return None, False

    ranked, used_current = score_recommendations(
        manga_df,
        profile,
        current_genres,
        current_themes,
        top_n=k,
    )
    return ranked, used_current
