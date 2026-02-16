"""Entry point that runs filtering and delegates scoring by algorithm version."""

from recommender.filtering import run_filters
from recommender.scoring import score_and_rank, score_and_rank_v2, score_and_rank_v3

def recommendation_scores(
    manga_df,
    profile,
    current_genres,
    current_themes,
    read_manga,
    top_n=20,
    mode="v3",
    reroll=False,
    seed=None,
    diversify=True,
    novelty=False,
    personalize=True,
    earliest_year=None,
    content_types=None,
    blacklist_genres=None,
    blacklist_themes=None,
    prefiltered_df=None,
    prefiltered_idx=None,
    precomputed=None,
):

    """Compute recommendation results for the requested user context."""
    if prefiltered_df is not None:
        filtered = prefiltered_df
    else:
        filtered = run_filters(
            manga_df,
            profile,
            read_manga,
            content_types=content_types,
            blacklist_genres=blacklist_genres,
            blacklist_themes=blacklist_themes,
        )
    mode = (mode or "v3").lower()
    if mode in {"v1", "legacy"}:
        ranked, used_current = score_and_rank(
            filtered,
            manga_df,
            profile,
            current_genres,
            current_themes,
            read_manga,
            top_n=top_n,
            reroll=reroll,
            seed=seed,
            diversify=diversify,
            novelty=novelty,
            personalize=personalize,
            earliest_year=earliest_year,
        )
    elif mode in {"v2", "unbias"}:
        ranked, used_current = score_and_rank_v2(
            filtered,
            manga_df,
            profile,
            current_genres,
            current_themes,
            read_manga,
            top_n=top_n,
            reroll=reroll,
            seed=seed,
            diversify=diversify,
            novelty=novelty,
            personalize=personalize,
            earliest_year=earliest_year,
        )
    else:
        ranked, used_current = score_and_rank_v3(
            filtered,
            manga_df,
            profile,
            current_genres,
            current_themes,
            read_manga,
            top_n=top_n,
            reroll=reroll,
            seed=seed,
            diversify=diversify,
            novelty=novelty,
            personalize=personalize,
            earliest_year=earliest_year,
            precomputed=precomputed,
            prefiltered_idx=prefiltered_idx,
        )

    return ranked, used_current
