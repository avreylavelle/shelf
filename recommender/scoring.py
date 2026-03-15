"""Scoring and ranking strategies for recommendation models."""

import re

import numpy as np
import pandas as pd

from recommender.constants import (
    HISTORY_GENRE_WEIGHT,
    HISTORY_THEME_WEIGHT,
    MATCH_VS_INTERNAL_WEIGHT,
    READ_TITLES_GENRE_WEIGHT,
    READ_TITLES_THEME_WEIGHT,
    REQUESTED_GENRE_WEIGHT,
    REQUESTED_THEME_WEIGHT,
)
from utils.parsing import parse_list


def compute_rating_affinities(manga_df, read_manga):
    """Build simple rating-driven genre/theme affinities."""
    genre_boost = {}
    theme_boost = {}
    rated_count = 0

    for manga_id, rating in read_manga.items():
        if rating is None:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue

        rated_count += 1
        local_weight = (rating_value - 5) / 5

        if "id" in manga_df.columns:
            row = manga_df[manga_df["id"] == manga_id]
        else:
            row = manga_df[manga_df["title_name"] == manga_id]
        if row.empty:
            continue

        genres = parse_list(row.iloc[0]["genres"])
        themes = parse_list(row.iloc[0]["themes"])

        if genres:
            per_genre = local_weight / len(genres)
            for genre in genres:
                genre_boost[genre] = genre_boost.get(genre, 0) + per_genre

        if themes:
            per_theme = local_weight / len(themes)
            for theme in themes:
                theme_boost[theme] = theme_boost.get(theme, 0) + per_theme

    if rated_count <= 0:
        return {}, {}

    genre_affinity = {genre: value / rated_count for genre, value in genre_boost.items()}
    theme_affinity = {theme: value / rated_count for theme, value in theme_boost.items()}
    return genre_affinity, theme_affinity



def combine_scores(match_score, internal_score):
    """Blend the model match score with the item internal score."""
    if internal_score > 0:
        return (
            (match_score * MATCH_VS_INTERNAL_WEIGHT)
            + (internal_score * (1 - MATCH_VS_INTERNAL_WEIGHT))
        )
    return match_score



def compute_rating_affinities_v2(manga_df, read_manga):
    """Build normalized rating affinities with softer negative influence."""
    genre_boost = {}
    theme_boost = {}

    for manga_id, rating in read_manga.items():
        if rating is None or rating == 0:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue

        local_weight = (rating_value - 5) / 5
        if local_weight < 0:
            local_weight = max(local_weight, -0.4)

        if "id" in manga_df.columns:
            row = manga_df[manga_df["id"] == manga_id]
        else:
            row = manga_df[manga_df["title_name"] == manga_id]
        if row.empty:
            continue

        genres = parse_list(row.iloc[0]["genres"])
        themes = parse_list(row.iloc[0]["themes"])

        if genres:
            per_genre = local_weight / max(len(genres), 1)
            for genre in genres:
                genre_boost[genre] = genre_boost.get(genre, 0) + per_genre

        if themes:
            per_theme = local_weight / max(len(themes), 1)
            for theme in themes:
                theme_boost[theme] = theme_boost.get(theme, 0) + per_theme

    def normalize(weights):
        denom = sum(abs(value) for value in weights.values())
        if denom <= 0:
            return {}
        return {key: value / denom for key, value in weights.items()}

    return normalize(genre_boost), normalize(theme_boost)



def _minmax(series):
    """Min-max normalize a pandas series."""
    if series.empty:
        return series
    min_value = series.min()
    max_value = series.max()
    if max_value == min_value:
        return series.apply(lambda _: 0.0)
    return (series - min_value) / (max_value - min_value)



def _soft_cap(score):
    """Keep scores in (0, 1) while preserving ordering."""
    return 1 - np.exp(-score)



def _vector_from_weights(weights, index_map, size):
    """Convert a sparse weight mapping into a dense vector."""
    if not weights or not index_map or size <= 0:
        return np.zeros(size, dtype=float)
    vector = np.zeros(size, dtype=float)
    for key, value in weights.items():
        idx = index_map.get(key)
        if idx is None:
            continue
        try:
            vector[idx] = float(value)
        except (TypeError, ValueError):
            continue
    return vector



def _collect_rated_indices(read_manga, id_index):
    """Collect rated candidate indices and numeric rating values."""
    indices = []
    ratings = []
    for manga_id, rating in read_manga.items():
        idx = id_index.get(manga_id)
        if idx is None or rating is None:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue
        indices.append(idx)
        ratings.append(rating_value)
    return np.array(indices, dtype=int), np.array(ratings, dtype=float)



def _compute_rating_affinities_v2_vec(read_manga, precomputed):
    """Vectorized normalized rating affinity construction."""
    indices, ratings = _collect_rated_indices(read_manga, precomputed.get("id_index", {}))
    if indices.size == 0:
        return (
            np.zeros(len(precomputed["genre_mlb"].classes_), dtype=float),
            np.zeros(len(precomputed["theme_mlb"].classes_), dtype=float),
        )

    nonzero_mask = ratings != 0
    indices = indices[nonzero_mask]
    ratings = ratings[nonzero_mask]
    if indices.size == 0:
        return (
            np.zeros(len(precomputed["genre_mlb"].classes_), dtype=float),
            np.zeros(len(precomputed["theme_mlb"].classes_), dtype=float),
        )

    local_weight = (ratings - 5) / 5
    local_weight = np.maximum(local_weight, -0.4)

    genre_counts = precomputed["genre_counts"][indices]
    theme_counts = precomputed["theme_counts"][indices]

    genre_weights = local_weight / np.maximum(genre_counts, 1)
    theme_weights = local_weight / np.maximum(theme_counts, 1)

    genre_boost = genre_weights @ precomputed["genre_matrix"][indices]
    theme_boost = theme_weights @ precomputed["theme_matrix"][indices]

    def normalize(vector):
        denom = np.sum(np.abs(vector))
        if denom <= 0:
            return np.zeros_like(vector, dtype=float)
        return vector / denom

    return normalize(genre_boost), normalize(theme_boost)



def _apply_earliest_year_bias_vectorized(combined_score, years, earliest_year):
    """Apply a capped penalty to items older than the preferred year."""
    if combined_score is None or not earliest_year or years is None:
        return combined_score
    try:
        earliest_year = int(earliest_year)
    except (TypeError, ValueError):
        return combined_score
    gap = earliest_year - years
    penalty = np.where(np.isfinite(gap) & (gap > 0), np.minimum(0.25, gap * 0.01), 0.0)
    return combined_score * (1 - penalty)



def _extract_year(text):
    """Extract a year from text when one is present."""
    if not text:
        return None
    match = re.search(r"(19\d{2}|20\d{2})", str(text))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None



def _apply_earliest_year_bias(df, earliest_year):
    """Apply the earliest-year preference to a ranked dataframe."""
    if not earliest_year:
        return df
    try:
        earliest_year = int(earliest_year)
    except (TypeError, ValueError):
        return df
    if "published_year" in df.columns:
        year_series = df["published_year"]
    elif "publishing_date" in df.columns:
        year_series = df["publishing_date"]
    else:
        return df

    years = pd.to_numeric(year_series, errors="coerce")
    if years.isna().any():
        years = years.fillna(year_series.astype(str).apply(_extract_year))

    def penalty(year):
        if year is None or year >= earliest_year:
            return 0.0
        return min(0.25, (earliest_year - year) * 0.01)

    penalties = years.apply(penalty)
    df["combined_score"] = df["combined_score"] * (1 - penalties)
    return df



def score_row(
    row,
    cur_genres,
    cur_themes,
    hist_genres,
    hist_themes,
    total_hist_genres,
    total_hist_themes,
    genre_affinity,
    theme_affinity,
):
    """Score a single row using the legacy blend."""
    used_current = False
    genres = set(row["genres"])
    themes = set(row["themes"])

    cur_genres_score = len(genres & cur_genres) / max(len(cur_genres), 1)
    cur_themes_score = len(themes & cur_themes) / max(len(cur_themes), 1)

    weighted_cur_genres = cur_genres_score * REQUESTED_GENRE_WEIGHT
    weighted_cur_themes = cur_themes_score * REQUESTED_THEME_WEIGHT
    if weighted_cur_genres > 0 or weighted_cur_themes > 0:
        used_current = True

    hist_genres_score = sum(hist_genres.get(genre, 0) for genre in genres) / total_hist_genres
    hist_themes_score = sum(hist_themes.get(theme, 0) for theme in themes) / total_hist_themes

    weighted_hist_genres = hist_genres_score * HISTORY_GENRE_WEIGHT
    weighted_hist_themes = hist_themes_score * HISTORY_THEME_WEIGHT

    rating_genre_boost = sum(genre_affinity.get(genre, 0) for genre in genres)
    rating_theme_boost = sum(theme_affinity.get(theme, 0) for theme in themes)

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



def score_row_v2(
    row,
    cur_genres,
    cur_themes,
    hist_genres,
    hist_themes,
    total_hist_genres,
    total_hist_themes,
    genre_affinity,
    theme_affinity,
):
    """Score a single row using the normalized v2 blend."""
    used_current = False
    genres = set(row["genres"])
    themes = set(row["themes"])

    cur_genres_score = len(genres & cur_genres) / max(len(cur_genres), 1)
    cur_themes_score = len(themes & cur_themes) / max(len(cur_themes), 1)

    weighted_cur_genres = cur_genres_score * REQUESTED_GENRE_WEIGHT
    weighted_cur_themes = cur_themes_score * REQUESTED_THEME_WEIGHT
    if weighted_cur_genres > 0 or weighted_cur_themes > 0:
        used_current = True

    hist_genres_score = sum(hist_genres.get(genre, 0) for genre in genres) / (
        total_hist_genres * max(len(genres), 1)
    )
    hist_themes_score = sum(hist_themes.get(theme, 0) for theme in themes) / (
        total_hist_themes * max(len(themes), 1)
    )

    weighted_hist_genres = hist_genres_score * HISTORY_GENRE_WEIGHT
    weighted_hist_themes = hist_themes_score * HISTORY_THEME_WEIGHT

    rating_genre_boost = sum(genre_affinity.get(genre, 0) for genre in genres) / max(len(genres), 1)
    rating_theme_boost = sum(theme_affinity.get(theme, 0) for theme in themes) / max(len(themes), 1)
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



def score_row_v3(
    row,
    cur_genres,
    cur_themes,
    hist_genres,
    hist_themes,
    total_hist_genres,
    total_hist_themes,
    genre_affinity,
    theme_affinity,
):
    """Score a single row using the balanced v3 blend."""
    return score_row_v2(
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



def _finalize_ranked(df, top_n):
    """Sort, dedupe, and limit the ranked dataframe."""
    ranked = df.sort_values("combined_score", ascending=False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")
    return ranked.head(top_n)



def _score_and_rank_v3_fast(
    filtered_df,
    profile,
    current_genres,
    current_themes,
    read_manga,
    top_n=20,
    earliest_year=None,
    precomputed=None,
    prefiltered_idx=None,
):
    """Vectorized v3 scoring path used by the web app."""
    df = filtered_df.copy()
    if precomputed is None or prefiltered_idx is None:
        return df.head(0), False

    row_idx = np.asarray(prefiltered_idx)
    genre_matrix = precomputed["genre_matrix"][row_idx]
    theme_matrix = precomputed["theme_matrix"][row_idx]
    genre_counts = precomputed["genre_counts"][row_idx]
    theme_counts = precomputed["theme_counts"][row_idx]

    genre_index = precomputed.get("genre_index", {})
    theme_index = precomputed.get("theme_index", {})

    cur_genre_idx = [genre_index[genre] for genre in current_genres if genre in genre_index]
    cur_theme_idx = [theme_index[theme] for theme in current_themes if theme in theme_index]

    if cur_genre_idx:
        cur_genre_hits = genre_matrix[:, cur_genre_idx].sum(axis=1)
    else:
        cur_genre_hits = np.zeros(len(df), dtype=float)
    if cur_theme_idx:
        cur_theme_hits = theme_matrix[:, cur_theme_idx].sum(axis=1)
    else:
        cur_theme_hits = np.zeros(len(df), dtype=float)

    used_current = bool((cur_genre_hits > 0).any() or (cur_theme_hits > 0).any())

    cur_genres_score = cur_genre_hits / max(len(current_genres), 1)
    cur_themes_score = cur_theme_hits / max(len(current_themes), 1)

    weighted_cur_genres = cur_genres_score * REQUESTED_GENRE_WEIGHT
    weighted_cur_themes = cur_themes_score * REQUESTED_THEME_WEIGHT

    hist_genres = profile.get("preferred_genres", {}) or {}
    hist_themes = profile.get("preferred_themes", {}) or {}
    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_vec = _vector_from_weights(hist_genres, genre_index, len(precomputed["genre_mlb"].classes_))
    theme_vec = _vector_from_weights(hist_themes, theme_index, len(precomputed["theme_mlb"].classes_))

    denom_genres = total_hist_genres * np.maximum(genre_counts, 1)
    denom_themes = total_hist_themes * np.maximum(theme_counts, 1)

    hist_genres_score = (genre_matrix @ genre_vec) / denom_genres
    hist_themes_score = (theme_matrix @ theme_vec) / denom_themes

    weighted_hist_genres = hist_genres_score * HISTORY_GENRE_WEIGHT
    weighted_hist_themes = hist_themes_score * HISTORY_THEME_WEIGHT

    genre_affinity, theme_affinity = _compute_rating_affinities_v2_vec(read_manga, precomputed)
    rating_genre_boost = (genre_matrix @ genre_affinity) / np.maximum(genre_counts, 1)
    rating_theme_boost = (theme_matrix @ theme_affinity) / np.maximum(theme_counts, 1)
    rating_genre_boost = np.maximum(rating_genre_boost, -0.2)
    rating_theme_boost = np.maximum(rating_theme_boost, -0.2)

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

    match_score = _soft_cap(total_score)
    if not used_current:
        match_score = match_score * (1 / (1 - (REQUESTED_GENRE_WEIGHT + REQUESTED_THEME_WEIGHT)))

    internal_score = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0).to_numpy() * 0.1
    internal_score = np.round(internal_score, 3)

    combined_score = np.where(
        internal_score > 0,
        (match_score * MATCH_VS_INTERNAL_WEIGHT) + (internal_score * (1 - MATCH_VS_INTERNAL_WEIGHT)),
        match_score,
    )

    years = precomputed.get("published_year")
    if years is not None:
        combined_score = _apply_earliest_year_bias_vectorized(combined_score, years[row_idx], earliest_year)

    df["match_score"] = match_score
    df["internal_score"] = internal_score
    df["combined_score"] = combined_score
    return _finalize_ranked(df, top_n), used_current



def score_and_rank_v3(
    filtered_df,
    manga_df,
    profile,
    current_genres,
    current_themes,
    read_manga,
    top_n=20,
    earliest_year=None,
    precomputed=None,
    prefiltered_idx=None,
):
    """Compute and rank results using the balanced v3 scorer."""
    if precomputed is not None and prefiltered_idx is not None:
        return _score_and_rank_v3_fast(
            filtered_df,
            profile,
            current_genres,
            current_themes,
            read_manga,
            top_n=top_n,
            earliest_year=earliest_year,
            precomputed=precomputed,
            prefiltered_idx=prefiltered_idx,
        )

    df = filtered_df.copy()
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
        score, used_current = score_row_v3(
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
        used_current_flags.append(used_current)

    df["match_score"] = match_scores
    used_current = any(used_current_flags)
    if not used_current:
        df["match_score"] = df["match_score"] * (1 / (1 - (REQUESTED_GENRE_WEIGHT + REQUESTED_THEME_WEIGHT)))

    df["match_score"] = df["match_score"].apply(_soft_cap)
    df["internal_score"] = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0).mul(0.1).round(3)
    df["combined_score"] = df.apply(
        lambda row: combine_scores(row["match_score"], row["internal_score"]),
        axis=1,
    )

    df = _apply_earliest_year_bias(df, earliest_year)
    return _finalize_ranked(df, top_n), used_current



def score_and_rank_v2(
    filtered_df,
    manga_df,
    profile,
    current_genres,
    current_themes,
    read_manga,
    top_n=20,
    earliest_year=None,
):
    """Compute and rank results using the relative v2 scorer."""
    df = filtered_df.copy()
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
        score, used_current = score_row_v2(
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
        used_current_flags.append(used_current)

    df["match_score"] = _minmax(pd.Series(match_scores, index=df.index))
    df["internal_score_raw"] = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0)
    df["internal_score"] = _minmax(df["internal_score_raw"]).fillna(0)
    df["combined_score"] = df.apply(
        lambda row: combine_scores(row["match_score"], row["internal_score"]),
        axis=1,
    )

    df = _apply_earliest_year_bias(df, earliest_year)
    return _finalize_ranked(df, top_n), any(used_current_flags)



def score_and_rank(
    filtered_df,
    manga_df,
    profile,
    current_genres,
    current_themes,
    read_manga,
    top_n=20,
    earliest_year=None,
):
    """Compute and rank results using the legacy scorer."""
    df = filtered_df.copy()
    cur_genres = set(current_genres)
    cur_themes = set(current_themes)

    hist_genres = profile.get("preferred_genres", {})
    hist_themes = profile.get("preferred_themes", {})
    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_affinity, theme_affinity = compute_rating_affinities(manga_df, read_manga)

    match_scores = []
    used_current_flags = []
    for _, row in df.iterrows():
        score, used_current = score_row(
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
        used_current_flags.append(used_current)

    df["match_score"] = match_scores
    used_current = any(used_current_flags)
    if not used_current:
        df["match_score"] = df["match_score"] * (1 / (1 - (REQUESTED_GENRE_WEIGHT + REQUESTED_THEME_WEIGHT)))

    df["match_score"] = df["match_score"].apply(_soft_cap)
    df["internal_score"] = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0).mul(0.1).round(3)
    df["combined_score"] = df.apply(
        lambda row: combine_scores(row["match_score"], row["internal_score"]),
        axis=1,
    )

    df = _apply_earliest_year_bias(df, earliest_year)
    return _finalize_ranked(df, top_n), used_current
