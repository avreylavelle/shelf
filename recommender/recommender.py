from recommender.filtering import run_filters
from recommender.scoring import score_and_rank, score_and_rank_v2, score_and_rank_v3

def recommendation_scores(manga_df, profile, current_genres, current_themes, read_manga, top_n=20, mode="v3", reroll=False, seed=None):

    filtered = run_filters(manga_df, profile, read_manga)
    mode = (mode or "v3").lower()
    if mode in {"v1", "legacy"}:
        ranked, used_current = score_and_rank(
            filtered, manga_df, profile, current_genres, current_themes, read_manga, top_n=top_n
        )
    elif mode in {"v2", "unbias"}:
        ranked, used_current = score_and_rank_v2(
            filtered, manga_df, profile, current_genres, current_themes, read_manga, top_n=top_n, reroll=reroll, seed=seed
        )
    else:
        ranked, used_current = score_and_rank_v3(
            filtered, manga_df, profile, current_genres, current_themes, read_manga, top_n=top_n, reroll=reroll, seed=seed
        )

    return ranked, used_current

