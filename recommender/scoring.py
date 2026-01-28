import pandas as pd
import numpy as np
from utils.parsing import parse_list
from recommender.constants import (
    REQUESTED_GENRE_WEIGHT,
    REQUESTED_THEME_WEIGHT,
    HISTORY_GENRE_WEIGHT,
    HISTORY_THEME_WEIGHT,
    READ_TITLES_GENRE_WEIGHT,
    READ_TITLES_THEME_WEIGHT,
    MATCH_VS_INTERNAL_WEIGHT,
)

def compute_rating_affinities(manga_df, read_manga):
    
    genre_boost = {}
    theme_boost = {}
    rated_count = 0

    # Iterate through all read entries
    for title, rating in read_manga.items():

        if rating is None:
            continue
        rated_count += 1
        local_weight = (rating - 5) / 5 # 10 gives a 1.0 boost, 1 gives a -0.8, 0 is ignored, 5 does nothing

        row = manga_df[manga_df["title_name"] == title] # row per title
        if row.empty: # skip entries with no rating
            continue

        # Genres and themes of the title
        genres = parse_list(row.iloc[0]["genres"]) # genres per row
        themes = parse_list(row.iloc[0]["themes"]) # themes per row

        # Compile all genres / themes that occur
        if genres:
            per_g = local_weight / len(genres) # the weight per genre
            for g in genres:
                genre_boost[g] = genre_boost.get(g, 0) + per_g # Compile total score for genre/rating (max 1.0, min -0.8)

        if themes:
            per_t = local_weight / len(themes) # the weight per theme
            for t in themes:
                theme_boost[t] = theme_boost.get(t, 0) + per_t # Compile total score for theme/rating (max 1.0, min -0.8)
        
    # Makes sure it isnt a 0, Normalize
    if rated_count > 0:
        genre_affinity = {g: genre_boost[g] / rated_count for g in genre_boost} # divide each genre weight by the # of rated, to fully normalize
        theme_affinity = {t: theme_boost[t] / rated_count for t in theme_boost} # divide each theme weight by the # of rated, to fully normalize
    else:
        genre_affinity = {}
        theme_affinity = {}

    return genre_affinity, theme_affinity

def score_row(row, cur_genres, cur_themes, hist_genres, hist_themes, total_hist_genres, total_hist_themes, genre_affinity, theme_affinity):
    
        # genres and themes from the row
        used_current = False
        genres = set(row["genres"])
        themes = set(row["themes"])

        # Compare the genres and themes requested to these genres and themes, divide by all request genres and themes
        cur_genres_score = len(genres & cur_genres) / max(len(cur_genres), 1)
        cur_themes_score = len(themes & cur_themes) / max(len(cur_themes), 1)

        weighted_cur_genres = cur_genres_score * REQUESTED_GENRE_WEIGHT
        weighted_cur_themes = cur_themes_score * REQUESTED_THEME_WEIGHT

        # Ensure the Currents are used. Adjusts recommendations later
        if weighted_cur_genres > 0 or weighted_cur_themes > 0:
            used_current = True

        # Same thing, but for the history ones.
        hist_genres_score = sum(hist_genres.get(g, 0) for g in genres) / total_hist_genres
        hist_themes_score = sum(hist_themes.get(t, 0) for t in themes) / total_hist_themes  

        weighted_hist_genres = hist_genres_score * HISTORY_GENRE_WEIGHT
        weighted_hist_themes = hist_themes_score * HISTORY_THEME_WEIGHT

        # Personalized to favorite titles and ratings
        rating_genre_boost = sum(genre_affinity.get(g, 0) for g in genres)
        rating_theme_boost = sum(theme_affinity.get(t, 0) for t in themes)

        weighted_rating_genres = rating_genre_boost * READ_TITLES_GENRE_WEIGHT
        weighted_rating_themes = rating_theme_boost * READ_TITLES_THEME_WEIGHT

        total_score = weighted_cur_genres + weighted_cur_themes + weighted_hist_genres + weighted_hist_themes + weighted_rating_genres + weighted_rating_themes

        return total_score, used_current
    
def combine_scores(match_score, internal_score):
    
    if internal_score > 0:
        return (
            (match_score * MATCH_VS_INTERNAL_WEIGHT)
            + (internal_score * (1 - MATCH_VS_INTERNAL_WEIGHT))
        )
    else:
        return match_score



def compute_rating_affinities_v2(manga_df, read_manga):
    genre_boost = {}
    theme_boost = {}

    for title, rating in read_manga.items():
        if rating is None or rating == 0:
            continue
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            continue

        local_weight = (rating - 5) / 5
        # soften negatives
        if local_weight < 0:
            local_weight = max(local_weight, -0.4)

        row = manga_df[manga_df["title_name"] == title]
        if row.empty:
            continue

        genres = parse_list(row.iloc[0]["genres"])
        themes = parse_list(row.iloc[0]["themes"])

        if genres:
            per_g = local_weight / max(len(genres), 1)
            for g in genres:
                genre_boost[g] = genre_boost.get(g, 0) + per_g

        if themes:
            per_t = local_weight / max(len(themes), 1)
            for t in themes:
                theme_boost[t] = theme_boost.get(t, 0) + per_t

    def normalize(weights):
        denom = sum(abs(v) for v in weights.values())
        if denom <= 0:
            return {}
        return {k: v / denom for k, v in weights.items()}

    return normalize(genre_boost), normalize(theme_boost)


def _minmax(series):
    if series.empty:
        return series
    min_v = series.min()
    max_v = series.max()
    if max_v == min_v:
        return series.apply(lambda _: 0.0)
    return (series - min_v) / (max_v - min_v)


def score_row_v2(row, cur_genres, cur_themes, hist_genres, hist_themes, total_hist_genres, total_hist_themes, genre_affinity, theme_affinity):
    used_current = False
    genres = set(row["genres"])
    themes = set(row["themes"])

    cur_genres_score = len(genres & cur_genres) / max(len(cur_genres), 1)
    cur_themes_score = len(themes & cur_themes) / max(len(cur_themes), 1)

    weighted_cur_genres = cur_genres_score * REQUESTED_GENRE_WEIGHT
    weighted_cur_themes = cur_themes_score * REQUESTED_THEME_WEIGHT

    if weighted_cur_genres > 0 or weighted_cur_themes > 0:
        used_current = True

    # normalize history by row size to avoid multi-tag bias
    hist_genres_score = sum(hist_genres.get(g, 0) for g in genres) / (total_hist_genres * max(len(genres), 1))
    hist_themes_score = sum(hist_themes.get(t, 0) for t in themes) / (total_hist_themes * max(len(themes), 1))

    weighted_hist_genres = hist_genres_score * HISTORY_GENRE_WEIGHT
    weighted_hist_themes = hist_themes_score * HISTORY_THEME_WEIGHT

    rating_genre_boost = sum(genre_affinity.get(g, 0) for g in genres) / max(len(genres), 1)
    rating_theme_boost = sum(theme_affinity.get(t, 0) for t in themes) / max(len(themes), 1)

    # clamp negative influence
    rating_genre_boost = max(rating_genre_boost, -0.2)
    rating_theme_boost = max(rating_theme_boost, -0.2)

    weighted_rating_genres = rating_genre_boost * READ_TITLES_GENRE_WEIGHT
    weighted_rating_themes = rating_theme_boost * READ_TITLES_THEME_WEIGHT

    total_score = (
        weighted_cur_genres
        + weighted_cur_themes
        + weighted_hist_genres
        + weighted_hist_themes
        + weighted_rating_genres
        + weighted_rating_themes
    )

    return total_score, used_current


def score_and_rank_v2(filtered_df, manga_df, profile, current_genres, current_themes, read_manga, top_n=20, reroll=False, seed=None, pool_multiplier=3, temperature=0.7):
    df = filtered_df.copy()
    used_current = False

    cur_genres = set(current_genres)
    cur_themes = set(current_themes)

    hist_genres = profile.get("preferred_genres", {})
    hist_themes = profile.get("preferred_themes", {})

    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_affinity, theme_affinity = compute_rating_affinities_v2(manga_df, read_manga)

    match_scores = []
    used_current_flags = []
    for _, row in df.iterrows():
        score, used_c = score_row_v2(
            row,
            cur_genres,
            cur_themes,
            hist_genres,
            hist_themes,
            total_hist_genres,
            total_hist_themes,
            genre_affinity,
            theme_affinity,
        )
        match_scores.append(score)
        used_current_flags.append(used_c)

    df["match_score_raw"] = match_scores
    df["match_score"] = _minmax(pd.Series(match_scores, index=df.index))

    df["internal_score_raw"] = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0)
    df["internal_score"] = _minmax(df["internal_score_raw"]).fillna(0)

    used_current = any(used_current_flags)

    df["combined_score"] = df.apply(
        lambda row: combine_scores(row["match_score"], row["internal_score"]), axis=1
    )

    ranked = df.sort_values("combined_score", ascending=False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")

    # Optional reroll: sample from top pool
    if reroll and len(ranked) > top_n:
        pool_size = min(len(ranked), max(top_n, top_n * pool_multiplier))
        pool = ranked.head(pool_size).copy()
        scores = pool["combined_score"].astype(float)
        if temperature <= 0:
            temperature = 0.7
        weights = (scores / temperature).apply(lambda x: np.exp(x))
        weights = weights / weights.sum() if weights.sum() > 0 else None
        if weights is not None:
            sample = pool.sample(n=top_n, replace=False, weights=weights, random_state=seed)
            ranked = sample
        else:
            ranked = pool.head(top_n)
    else:
        ranked = ranked.head(top_n)

    return ranked, used_current

def score_and_rank(filtered_df, manga_df, profile, current_genres, current_themes, read_manga, top_n=20):
    df = filtered_df.copy()
    used_current = False

    # Current requested genres and themes
    cur_genres = set(current_genres)
    cur_themes = set(current_themes)

    # These are the genres and themes on the users profile from previous entries
    hist_genres = profile.get("preferred_genres", {})
    hist_themes = profile.get("preferred_themes", {})

    # Sum of all genres and themes
    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_affinity, theme_affinity = compute_rating_affinities(manga_df, read_manga)

    match_scores = []
    used_current_flags = []
    for _, row in df.iterrows():
        score, used_c = score_row(
            row,
            cur_genres,
            cur_themes,
            hist_genres,
            hist_themes,
            total_hist_genres,
            total_hist_themes,
            genre_affinity,
            theme_affinity
        )

        match_scores.append(score)
        used_current_flags.append(used_c)


    # Run the previous function 
    df["match_score"] = match_scores

    # Make a df for the internal score from the database
    df["internal_score"] = pd.to_numeric(df.get("score", 0), errors = "coerce").fillna(0).mul(0.1).round(3)

    used_current = any(used_current_flags)

    if used_current:
        df["match_score"] = df["match_score"] * 1
    else:
        df["match_score"] = df["match_score"] * (1 / (1 - (REQUESTED_GENRE_WEIGHT + REQUESTED_THEME_WEIGHT))) # Normalize if not using current

    combined_scores = []

    for i, row in df.iterrows():
        match_score = row["match_score"]
        internal_score = row["internal_score"]

        final_score = combine_scores(match_score, internal_score)
        combined_scores.append(final_score)

    df["combined_score"] = combined_scores

    ranked = df.sort_values("combined_score", ascending = False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")
    ranked = ranked.head(top_n)
    return ranked, used_current
    
