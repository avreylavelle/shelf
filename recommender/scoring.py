"""Scoring and ranking strategies for recommendation models."""

import pandas as pd
import numpy as np
import re
from collections import Counter
from utils.parsing import parse_list
from recommender.constants import (
    REQUESTED_GENRE_WEIGHT,
    REQUESTED_THEME_WEIGHT,
    HISTORY_GENRE_WEIGHT,
    HISTORY_THEME_WEIGHT,
    READ_TITLES_GENRE_WEIGHT,
    READ_TITLES_THEME_WEIGHT,
    MATCH_VS_INTERNAL_WEIGHT,
    NOVELTY_WEIGHT,
    SIGNAL_GENRE_WEIGHT,
    SIGNAL_THEME_WEIGHT,
    PERSONALIZATION_MIN_RATINGS,
    PERSONALIZATION_FULL_RATINGS,
)

def compute_rating_affinities(manga_df, read_manga):
    
    """Handle compute rating affinities for this module."""
    genre_boost = {}
    theme_boost = {}
    rated_count = 0

    # Iterate through all read entries
    for manga_id, rating in read_manga.items():

        if rating is None:
            continue
        rated_count += 1
        local_weight = (rating - 5) / 5 # 10 gives a 1.0 boost, 1 gives a -0.8, 0 is ignored, 5 does nothing

        if "id" in manga_df.columns:
            row = manga_df[manga_df["id"] == manga_id]
        else:
            row = manga_df[manga_df["title_name"] == manga_id]
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
    
    """Combine scores into one value."""
    if internal_score > 0:
        return (
            (match_score * MATCH_VS_INTERNAL_WEIGHT)
            + (internal_score * (1 - MATCH_VS_INTERNAL_WEIGHT))
        )
    else:
        return match_score



def compute_rating_affinities_v2(manga_df, read_manga):
    """Handle compute rating affinities v2 for this module."""
    genre_boost = {}
    theme_boost = {}

    for manga_id, rating in read_manga.items():
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

        if "id" in manga_df.columns:
            row = manga_df[manga_df["id"] == manga_id]
        else:
            row = manga_df[manga_df["title_name"] == manga_id]
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
        """Normalize values for consistent comparisons."""
        denom = sum(abs(v) for v in weights.values())
        if denom <= 0:
            return {}
        return {k: v / denom for k, v in weights.items()}

    return normalize(genre_boost), normalize(theme_boost)


def _minmax(series):
    """Handle minmax for this module."""
    if series.empty:
        return series
    min_v = series.min()
    max_v = series.max()
    if max_v == min_v:
        return series.apply(lambda _: 0.0)
    return (series - min_v) / (max_v - min_v)


def _series_key(title):
    """Handle series key for this module."""
    if not title:
        return ""
    text = str(title).lower()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.split(r"[:\\-–—]", text)[0]
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return text


def _personalization_strength(rated_count, enabled=True):
    """Handle personalization strength for this module."""
    if not enabled:
        return 0.0
    if rated_count is None:
        return 0.0
    if rated_count < PERSONALIZATION_MIN_RATINGS:
        return 0.0
    if rated_count >= PERSONALIZATION_FULL_RATINGS:
        return 1.0
    span = PERSONALIZATION_FULL_RATINGS - PERSONALIZATION_MIN_RATINGS
    return max(0.0, min(1.0, (rated_count - PERSONALIZATION_MIN_RATINGS) / max(span, 1)))


def _soft_cap(score):
    # Keeps scores in (0,1) while preserving ordering for larger values.
    return 1 - np.exp(-score)


def _vector_from_weights(weights, index_map, size):
    """Handle vector from weights for this module."""
    if not weights or not index_map or size <= 0:
        return np.zeros(size, dtype=float)
    vec = np.zeros(size, dtype=float)
    for key, value in weights.items():
        idx = index_map.get(key)
        if idx is None:
            continue
        try:
            vec[idx] = float(value)
        except (TypeError, ValueError):
            continue
    return vec


def _collect_rated_indices(read_manga, id_index):
    """Handle collect rated indices for this module."""
    indices = []
    ratings = []
    for manga_id, rating in read_manga.items():
        idx = id_index.get(manga_id)
        if idx is None:
            continue
        if rating is None:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue
        indices.append(idx)
        ratings.append(rating_value)
    return np.array(indices, dtype=int), np.array(ratings, dtype=float)


def _compute_rating_affinities_v2_vec(read_manga, precomputed):
    """Handle compute rating affinities v2 vec for this module."""
    indices, ratings = _collect_rated_indices(read_manga, precomputed.get("id_index", {}))
    if indices.size == 0:
        return np.zeros(len(precomputed["genre_mlb"].classes_), dtype=float), np.zeros(
            len(precomputed["theme_mlb"].classes_), dtype=float
        )

    # Drop zero ratings
    mask = ratings != 0
    indices = indices[mask]
    ratings = ratings[mask]
    if indices.size == 0:
        return np.zeros(len(precomputed["genre_mlb"].classes_), dtype=float), np.zeros(
            len(precomputed["theme_mlb"].classes_), dtype=float
        )

    local_weight = (ratings - 5) / 5
    local_weight = np.maximum(local_weight, -0.4)

    genre_counts = precomputed["genre_counts"][indices]
    theme_counts = precomputed["theme_counts"][indices]

    g_weights = local_weight / np.maximum(genre_counts, 1)
    t_weights = local_weight / np.maximum(theme_counts, 1)

    genre_boost = g_weights @ precomputed["genre_matrix"][indices]
    theme_boost = t_weights @ precomputed["theme_matrix"][indices]

    def normalize(vec):
        """Normalize values for consistent comparisons."""
        denom = np.sum(np.abs(vec))
        if denom <= 0:
            return np.zeros_like(vec, dtype=float)
        return vec / denom

    return normalize(genre_boost), normalize(theme_boost)


def _apply_earliest_year_bias_vectorized(combined_score, years, earliest_year):
    """Handle apply earliest year bias vectorized for this module."""
    if combined_score is None:
        return combined_score
    if not earliest_year:
        return combined_score
    try:
        earliest_year = int(earliest_year)
    except (TypeError, ValueError):
        return combined_score
    if years is None:
        return combined_score
    gap = earliest_year - years
    penalty = np.where(np.isfinite(gap) & (gap > 0), np.minimum(0.25, gap * 0.01), 0.0)
    return combined_score * (1 - penalty)

def _extract_year(text):
    """Handle extract year for this module."""
    if not text:
        return None
    match = re.search(r"(19\\d{2}|20\\d{2})", str(text))
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _apply_earliest_year_bias(df, earliest_year):
    """Handle apply earliest year bias for this module."""
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
        extracted = year_series.astype(str).apply(_extract_year)
        years = years.fillna(extracted)
    def penalty(year):
        """Handle penalty for this module."""
        if year is None:
            return 0.0
        if year >= earliest_year:
            return 0.0
        gap = earliest_year - year
        return min(0.25, gap * 0.01)
    penalties = years.apply(penalty)
    df["combined_score"] = df["combined_score"] * (1 - penalties)
    return df


def _apply_novelty(df, weight=NOVELTY_WEIGHT):
    """Handle apply novelty for this module."""
    if weight <= 0:
        return df
    novelty = None
    if "members" in df.columns:
        members = pd.to_numeric(df["members"], errors="coerce").fillna(0)
        novelty = 1 - _minmax(np.log1p(members))
    elif "popularity" in df.columns:
        popularity = pd.to_numeric(df["popularity"], errors="coerce")
        novelty = _minmax(popularity.fillna(popularity.max() if popularity.notna().any() else 0))
    elif "scored_by" in df.columns:
        scored_by = pd.to_numeric(df["scored_by"], errors="coerce").fillna(0)
        novelty = 1 - _minmax(np.log1p(scored_by))
    if novelty is None:
        return df
    df["novelty_score"] = novelty.fillna(0)
    df["combined_score"] = (1 - weight) * df["combined_score"] + weight * df["novelty_score"]
    return df


def _weighted_sample(df, n, temperature=0.7, seed=None):
    """Handle weighted sample for this module."""
    if n <= 0 or df.empty:
        return df.head(0)
    scores = df["combined_score"].astype(float)
    if temperature <= 0:
        temperature = 0.7
    weights = (scores / temperature).apply(lambda x: np.exp(x))
    weights = weights / weights.sum() if weights.sum() > 0 else None
    if weights is not None:
        return df.sample(n=n, replace=False, weights=weights, random_state=seed)
    return df.head(n)


def _reroll_candidates(ranked, top_n, pool_multiplier=3, temperature=0.7, seed=None):
    """Handle reroll candidates for this module."""
    if ranked.empty or len(ranked) <= top_n:
        return ranked, ranked.head(0)
    pool_size = min(len(ranked), max(top_n, top_n * pool_multiplier))
    pool = ranked.head(pool_size).copy()
    anchor_n = max(1, int(top_n * 0.3))
    anchors = pool.head(anchor_n)
    remainder = pool.iloc[anchor_n:]
    sample_n = min(len(remainder), max(top_n * 2, top_n) - anchor_n)
    sampled = _weighted_sample(remainder, sample_n, temperature=temperature, seed=seed)
    candidates = pd.concat([anchors, sampled])
    candidates = candidates[~candidates.index.duplicated(keep="first")]
    return candidates, anchors


def _select_diverse(df, top_n, required=None):
    """Handle select diverse for this module."""
    if df.empty:
        return df
    max_genre = max(3, top_n // 3)
    max_theme = max(2, top_n // 4)
    selected_idx = []
    seen_idx = set()
    genre_counts = Counter()
    theme_counts = Counter()
    series_counts = Counter()
    fallback = []

    def add_row(idx, row, force=False):
        """Add row to storage."""
        if idx in seen_idx:
            return False
        title = row.get("title_name") or row.get("title") or row.get("english_name") or ""
        key = _series_key(title)
        genres = set(row.get("genres") or [])
        themes = set(row.get("themes") or [])
        if not force:
            if key and series_counts[key] >= 1:
                return False
            if any(genre_counts[g] >= max_genre for g in genres):
                return False
            if any(theme_counts[t] >= max_theme for t in themes):
                return False
        selected_idx.append(idx)
        seen_idx.add(idx)
        if key:
            series_counts[key] += 1
        for g in genres:
            genre_counts[g] += 1
        for t in themes:
            theme_counts[t] += 1
        return True

    if required is not None and not required.empty:
        for idx, row in required.iterrows():
            add_row(idx, row, force=True)

    for idx, row in df.iterrows():
        if idx in seen_idx:
            continue
        if add_row(idx, row, force=False):
            if len(selected_idx) >= top_n:
                break
        else:
            fallback.append((idx, row))

    if len(selected_idx) < top_n:
        for idx, row in fallback:
            if idx in seen_idx:
                continue
            add_row(idx, row, force=True)
            if len(selected_idx) >= top_n:
                break

    return df.loc[selected_idx]


def score_row_v2(row, cur_genres, cur_themes, hist_genres, hist_themes, total_hist_genres, total_hist_themes, genre_affinity, theme_affinity, signal_genres, signal_themes, signal_strength):
    """Compute row v2 for ranking."""
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

    signal_genre_boost = sum(signal_genres.get(g, 0) for g in genres) / max(len(genres), 1)
    signal_theme_boost = sum(signal_themes.get(t, 0) for t in themes) / max(len(themes), 1)
    signal_genre_boost = max(min(signal_genre_boost, 0.25), -0.25)
    signal_theme_boost = max(min(signal_theme_boost, 0.25), -0.25)

    weighted_signal_genres = signal_genre_boost * SIGNAL_GENRE_WEIGHT * signal_strength
    weighted_signal_themes = signal_theme_boost * SIGNAL_THEME_WEIGHT * signal_strength

    total_score = (
        weighted_cur_genres
        + weighted_cur_themes
        + weighted_hist_genres
        + weighted_hist_themes
        + weighted_rating_genres
        + weighted_rating_themes
        + weighted_signal_genres
        + weighted_signal_themes
    )

    return total_score, used_current




def score_row_v3(row, cur_genres, cur_themes, hist_genres, hist_themes, total_hist_genres, total_hist_themes, genre_affinity, theme_affinity, signal_genres, signal_themes, signal_strength):
    """Compute row v3 for ranking."""
    used_current = False
    genres = set(row["genres"])
    themes = set(row["themes"])

    cur_genres_score = len(genres & cur_genres) / max(len(cur_genres), 1)
    cur_themes_score = len(themes & cur_themes) / max(len(cur_themes), 1)

    weighted_cur_genres = cur_genres_score * REQUESTED_GENRE_WEIGHT
    weighted_cur_themes = cur_themes_score * REQUESTED_THEME_WEIGHT

    if weighted_cur_genres > 0 or weighted_cur_themes > 0:
        used_current = True

    # Normalize history by row size to reduce multi-tag bias
    hist_genres_score = sum(hist_genres.get(g, 0) for g in genres) / (total_hist_genres * max(len(genres), 1))
    hist_themes_score = sum(hist_themes.get(t, 0) for t in themes) / (total_hist_themes * max(len(themes), 1))

    weighted_hist_genres = hist_genres_score * HISTORY_GENRE_WEIGHT
    weighted_hist_themes = hist_themes_score * HISTORY_THEME_WEIGHT

    rating_genre_boost = sum(genre_affinity.get(g, 0) for g in genres) / max(len(genres), 1)
    rating_theme_boost = sum(theme_affinity.get(t, 0) for t in themes) / max(len(themes), 1)

    # Clamp negative influence
    rating_genre_boost = max(rating_genre_boost, -0.2)
    rating_theme_boost = max(rating_theme_boost, -0.2)

    weighted_rating_genres = rating_genre_boost * READ_TITLES_GENRE_WEIGHT
    weighted_rating_themes = rating_theme_boost * READ_TITLES_THEME_WEIGHT

    signal_genre_boost = sum(signal_genres.get(g, 0) for g in genres) / max(len(genres), 1)
    signal_theme_boost = sum(signal_themes.get(t, 0) for t in themes) / max(len(themes), 1)
    signal_genre_boost = max(min(signal_genre_boost, 0.25), -0.25)
    signal_theme_boost = max(min(signal_theme_boost, 0.25), -0.25)

    weighted_signal_genres = signal_genre_boost * SIGNAL_GENRE_WEIGHT * signal_strength
    weighted_signal_themes = signal_theme_boost * SIGNAL_THEME_WEIGHT * signal_strength

    total_score = (
        weighted_cur_genres
        + weighted_cur_themes
        + weighted_hist_genres
        + weighted_hist_themes
        + weighted_rating_genres
        + weighted_rating_themes
        + weighted_signal_genres
        + weighted_signal_themes
    )

    return total_score, used_current


def _score_and_rank_v3_fast(
    filtered_df,
    profile,
    current_genres,
    current_themes,
    read_manga,
    top_n=20,
    reroll=False,
    seed=None,
    pool_multiplier=3,
    temperature=0.7,
    diversify=True,
    novelty=False,
    personalize=True,
    earliest_year=None,
    precomputed=None,
    prefiltered_idx=None,
):
    """Compute and rank v3 fast for ranking."""
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

    cur_genre_idx = [genre_index[g] for g in current_genres if g in genre_index]
    cur_theme_idx = [theme_index[t] for t in current_themes if t in theme_index]

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
    signal_genres = profile.get("signal_genres", {}) or {}
    signal_themes = profile.get("signal_themes", {}) or {}

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

    rated_count = sum(1 for v in read_manga.values() if v is not None)
    signal_strength = _personalization_strength(rated_count, personalize)

    signal_genre_vec = _vector_from_weights(signal_genres, genre_index, len(precomputed["genre_mlb"].classes_))
    signal_theme_vec = _vector_from_weights(signal_themes, theme_index, len(precomputed["theme_mlb"].classes_))

    signal_genre_boost = (genre_matrix @ signal_genre_vec) / np.maximum(genre_counts, 1)
    signal_theme_boost = (theme_matrix @ signal_theme_vec) / np.maximum(theme_counts, 1)
    signal_genre_boost = np.clip(signal_genre_boost, -0.25, 0.25)
    signal_theme_boost = np.clip(signal_theme_boost, -0.25, 0.25)

    weighted_signal_genres = signal_genre_boost * SIGNAL_GENRE_WEIGHT * signal_strength
    weighted_signal_themes = signal_theme_boost * SIGNAL_THEME_WEIGHT * signal_strength

    total_score = (
        weighted_cur_genres
        + weighted_cur_themes
        + weighted_hist_genres
        + weighted_hist_themes
        + weighted_rating_genres
        + weighted_rating_themes
        + weighted_signal_genres
        + weighted_signal_themes
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

    ranked = df.sort_values("combined_score", ascending=False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")

    if novelty:
        ranked = _apply_novelty(ranked, NOVELTY_WEIGHT)

    if reroll:
        candidates, anchors = _reroll_candidates(ranked, top_n, pool_multiplier=pool_multiplier, temperature=temperature, seed=seed)
        if diversify:
            ranked = _select_diverse(candidates, top_n, required=anchors)
        else:
            ranked = _weighted_sample(candidates, min(top_n, len(candidates)), temperature=temperature, seed=seed)
    else:
        if diversify:
            ranked = _select_diverse(ranked, top_n)
        else:
            ranked = ranked.head(top_n)

    return ranked, used_current


def score_and_rank_v3(filtered_df, manga_df, profile, current_genres, current_themes, read_manga, top_n=20, reroll=False, seed=None, pool_multiplier=3, temperature=0.7, diversify=True, novelty=False, personalize=True, earliest_year=None, precomputed=None, prefiltered_idx=None):
    """Compute and rank v3 for ranking."""
    df = filtered_df.copy()
    used_current = False

    if precomputed is not None and prefiltered_idx is not None:
        return _score_and_rank_v3_fast(
            filtered_df,
            profile,
            current_genres,
            current_themes,
            read_manga,
            top_n=top_n,
            reroll=reroll,
            seed=seed,
            pool_multiplier=pool_multiplier,
            temperature=temperature,
            diversify=diversify,
            novelty=novelty,
            personalize=personalize,
            earliest_year=earliest_year,
            precomputed=precomputed,
            prefiltered_idx=prefiltered_idx,
        )

    cur_genres = set(current_genres)
    cur_themes = set(current_themes)

    hist_genres = profile.get("preferred_genres", {})
    hist_themes = profile.get("preferred_themes", {})
    signal_genres = profile.get("signal_genres", {})
    signal_themes = profile.get("signal_themes", {})

    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_affinity, theme_affinity = compute_rating_affinities_v2(manga_df, read_manga)
    rated_count = sum(1 for v in read_manga.values() if v is not None)
    signal_strength = _personalization_strength(rated_count, personalize)

    match_scores = []
    used_current_flags = []
    for _, row in df.iterrows():
        score, used_c = score_row_v3(
            row,
            cur_genres,
            cur_themes,
            hist_genres,
            hist_themes,
            total_hist_genres,
            total_hist_themes,
            genre_affinity,
            theme_affinity,
            signal_genres,
            signal_themes,
            signal_strength,
        )
        match_scores.append(score)
        used_current_flags.append(used_c)

    df["match_score"] = match_scores

    used_current = any(used_current_flags)

    if used_current:
        df["match_score"] = df["match_score"] * 1
    else:
        df["match_score"] = df["match_score"] * (1 / (1 - (REQUESTED_GENRE_WEIGHT + REQUESTED_THEME_WEIGHT)))

    df["match_score"] = df["match_score"].apply(_soft_cap)

    # Internal score uses original scaling (0-10 -> 0-1)
    df["internal_score"] = pd.to_numeric(df.get("score", 0), errors="coerce").fillna(0).mul(0.1).round(3)

    combined_scores = []
    for _, row in df.iterrows():
        combined_scores.append(combine_scores(row["match_score"], row["internal_score"]))

    df["combined_score"] = combined_scores

    df = _apply_earliest_year_bias(df, earliest_year)

    ranked = df.sort_values("combined_score", ascending=False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")

    if novelty:
        ranked = _apply_novelty(ranked, NOVELTY_WEIGHT)

    if reroll:
        candidates, anchors = _reroll_candidates(ranked, top_n, pool_multiplier=pool_multiplier, temperature=temperature, seed=seed)
        if diversify:
            ranked = _select_diverse(candidates, top_n, required=anchors)
        else:
            ranked = _weighted_sample(candidates, min(top_n, len(candidates)), temperature=temperature, seed=seed)
    else:
        if diversify:
            ranked = _select_diverse(ranked, top_n)
        else:
            ranked = ranked.head(top_n)

    return ranked, used_current

def score_and_rank_v2(filtered_df, manga_df, profile, current_genres, current_themes, read_manga, top_n=20, reroll=False, seed=None, pool_multiplier=3, temperature=0.7, diversify=True, novelty=False, personalize=True, earliest_year=None):
    """Compute and rank v2 for ranking."""
    df = filtered_df.copy()
    used_current = False

    cur_genres = set(current_genres)
    cur_themes = set(current_themes)

    hist_genres = profile.get("preferred_genres", {})
    hist_themes = profile.get("preferred_themes", {})
    signal_genres = profile.get("signal_genres", {})
    signal_themes = profile.get("signal_themes", {})

    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_affinity, theme_affinity = compute_rating_affinities_v2(manga_df, read_manga)
    rated_count = sum(1 for v in read_manga.values() if v is not None)
    signal_strength = _personalization_strength(rated_count, personalize)

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
            signal_genres,
            signal_themes,
            signal_strength,
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

    df = _apply_earliest_year_bias(df, earliest_year)

    ranked = df.sort_values("combined_score", ascending=False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")

    if novelty:
        ranked = _apply_novelty(ranked, NOVELTY_WEIGHT)

    if reroll:
        candidates, anchors = _reroll_candidates(ranked, top_n, pool_multiplier=pool_multiplier, temperature=temperature, seed=seed)
        if diversify:
            ranked = _select_diverse(candidates, top_n, required=anchors)
        else:
            ranked = _weighted_sample(candidates, min(top_n, len(candidates)), temperature=temperature, seed=seed)
    else:
        if diversify:
            ranked = _select_diverse(ranked, top_n)
        else:
            ranked = ranked.head(top_n)

    return ranked, used_current

def score_and_rank(filtered_df, manga_df, profile, current_genres, current_themes, read_manga, top_n=20, reroll=False, seed=None, pool_multiplier=3, temperature=0.7, diversify=True, novelty=False, personalize=True, earliest_year=None):
    """Compute and rank for ranking."""
    df = filtered_df.copy()
    used_current = False

    # Current requested genres and themes
    cur_genres = set(current_genres)
    cur_themes = set(current_themes)

    # These are the genres and themes on the users profile from previous entries
    hist_genres = profile.get("preferred_genres", {})
    hist_themes = profile.get("preferred_themes", {})
    signal_genres = profile.get("signal_genres", {})
    signal_themes = profile.get("signal_themes", {})

    # Sum of all genres and themes
    total_hist_genres = sum(hist_genres.values()) or 1
    total_hist_themes = sum(hist_themes.values()) or 1

    genre_affinity, theme_affinity = compute_rating_affinities(manga_df, read_manga)
    rated_count = sum(1 for v in read_manga.values() if v is not None)
    signal_strength = _personalization_strength(rated_count, personalize)

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
        if signal_strength > 0 and (signal_genres or signal_themes):
            row_genres = set(row.get("genres") or [])
            row_themes = set(row.get("themes") or [])
            signal_genre_boost = sum(signal_genres.get(g, 0) for g in row_genres) / max(len(row_genres), 1)
            signal_theme_boost = sum(signal_themes.get(t, 0) for t in row_themes) / max(len(row_themes), 1)
            signal_genre_boost = max(min(signal_genre_boost, 0.25), -0.25)
            signal_theme_boost = max(min(signal_theme_boost, 0.25), -0.25)
            score += (signal_genre_boost * SIGNAL_GENRE_WEIGHT * signal_strength)
            score += (signal_theme_boost * SIGNAL_THEME_WEIGHT * signal_strength)

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

    df["match_score"] = df["match_score"].apply(_soft_cap)

    combined_scores = []

    for i, row in df.iterrows():
        match_score = row["match_score"]
        internal_score = row["internal_score"]

        final_score = combine_scores(match_score, internal_score)
        combined_scores.append(final_score)

    df["combined_score"] = combined_scores

    df = _apply_earliest_year_bias(df, earliest_year)

    ranked = df.sort_values("combined_score", ascending = False)
    if "title_name" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["title_name"], keep="first")
    elif "id" in ranked.columns:
        ranked = ranked.drop_duplicates(subset=["id"], keep="first")

    if novelty:
        ranked = _apply_novelty(ranked, NOVELTY_WEIGHT)

    if reroll:
        candidates, anchors = _reroll_candidates(ranked, top_n, pool_multiplier=pool_multiplier, temperature=temperature, seed=seed)
        if diversify:
            ranked = _select_diverse(candidates, top_n, required=anchors)
        else:
            ranked = _weighted_sample(candidates, min(top_n, len(candidates)), temperature=temperature, seed=seed)
    else:
        if diversify:
            ranked = _select_diverse(ranked, top_n)
        else:
            ranked = ranked.head(top_n)

    return ranked, used_current
    
