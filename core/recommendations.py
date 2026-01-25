from recommender.recommender import recommendation_scores


def score_recommendations(
    manga_df, profile, current_genres, current_themes, read_manga, top_n=20
):
    return recommendation_scores(
        manga_df, profile, current_genres, current_themes, read_manga, top_n=top_n
    )
