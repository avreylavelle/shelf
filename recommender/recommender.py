from recommender.filtering import run_filters
from recommender.scoring import score_and_rank

def recommendation_scores(manga_df, profile, current_genres, current_themes, read_manga, top_n=20):

    filtered = run_filters(manga_df, profile, read_manga)
    ranked, used_current = score_and_rank(
        filtered, manga_df, profile, current_genres, current_themes, read_manga, top_n=top_n
    )

    return ranked, used_current

