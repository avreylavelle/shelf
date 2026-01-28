import os
import sqlite3

import pandas as pd

from app.repos import profile as profile_repo
from app.repos import ratings as ratings_repo
from app.services import dnr as dnr_service
from app.services import reading_list as reading_list_service
from recommender.recommender import recommendation_scores
from utils.lookup import get_all_unique
from utils.parsing import parse_list

_MANGA_CACHE = {}
_OPTIONS_CACHE = {}


def _display_title_for_row(row, language):
    if language == "Japanese":
        return row.get("japanese_name") or row.get("title_name") or row.get("english_name") or ""
    return row.get("english_name") or row.get("title_name") or row.get("japanese_name") or ""


def _build_rated_lookup(manga_df, read_manga, language):
    if manga_df is None or manga_df.empty or not read_manga:
        return {}, {}
    genre_best = {}
    theme_best = {}
    for title, rating in read_manga.items():
        if rating is None:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue
        if rating_value <= 0:
            continue
        try:
            matches = manga_df[manga_df["title_name"] == title]
        except Exception:
            matches = None
        if matches is None or matches.empty:
            continue
        row = matches.iloc[0]
        display_title = _display_title_for_row(row, language)
        genres = parse_list(row.get("genres"))
        themes = parse_list(row.get("themes"))
        for g in genres:
            current = genre_best.get(g)
            if current is None or rating_value > current[1]:
                genre_best[g] = (display_title or title, rating_value)
        for t in themes:
            current = theme_best.get(t)
            if current is None or rating_value > current[1]:
                theme_best[t] = (display_title or title, rating_value)
    return genre_best, theme_best


def _explain_row(row, current_genres, current_themes, profile, genre_best, theme_best):
    reasons = []
    row_genres = set(row.get("genres") or [])
    row_themes = set(row.get("themes") or [])
    current_genres = set(current_genres or [])
    current_themes = set(current_themes or [])

    for g in sorted(row_genres & current_genres)[:2]:
        reasons.append(f"Requested genre: {g}")
    for t in sorted(row_themes & current_themes)[:2]:
        reasons.append(f"Requested theme: {t}")

    best = None
    for g in row_genres:
        candidate = genre_best.get(g)
        if candidate and (best is None or candidate[1] > best[1]):
            best = candidate
    for t in row_themes:
        candidate = theme_best.get(t)
        if candidate and (best is None or candidate[1] > best[1]):
            best = candidate
    if best:
        title, rating = best
        reasons.append(f"Because you rated {title} ({rating:.1f})")

    if len(reasons) < 3:
        preferred_genres = profile.get("preferred_genres", {})
        preferred_themes = profile.get("preferred_themes", {})
        top_genres = sorted(preferred_genres, key=preferred_genres.get, reverse=True)
        top_themes = sorted(preferred_themes, key=preferred_themes.get, reverse=True)
        for g in top_genres:
            if g in row_genres:
                reasons.append(f"From your history: {g}")
                break
        if len(reasons) < 3:
            for t in top_themes:
                if t in row_themes:
                    reasons.append(f"From your history: {t}")
                    break

    return reasons[:3]


def _resolve_db_path(db_path):
    if db_path:
        db_path = os.path.expandvars(os.path.expanduser(db_path))
        if not os.path.isabs(db_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            db_path = os.path.join(base_dir, db_path)
        return os.path.abspath(db_path)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "data", "db", "manga.db")


def _load_manga_df(db_path):
    cached = _MANGA_CACHE.get(db_path)
    if cached is not None:
        return cached
    conn = sqlite3.connect(db_path)
    try:
        df = pd.read_sql_query("SELECT * FROM manga_cleaned", conn)
    finally:
        conn.close()
    _MANGA_CACHE[db_path] = df
    return df


def get_available_options(db_path=None):
    db_path = _resolve_db_path(db_path)
    cached = _OPTIONS_CACHE.get(db_path)
    if cached is not None:
        return cached
    manga_df = _load_manga_df(db_path)
    genres = get_all_unique(manga_df, "genres")
    themes = get_all_unique(manga_df, "themes")
    _OPTIONS_CACHE[db_path] = (genres, themes)
    return genres, themes


def recommend_for_user(db_path, user_id, current_genres, current_themes, limit=20, mode=None, reroll=False, seed=None, diversify=True, novelty=False, personalize=True, earliest_year=None, content_types=None):
    db_path = _resolve_db_path(db_path)
    mode = (mode or os.environ.get("RECOMMENDER_MODE", "v3")).lower()
    profile = profile_repo.get_profile(user_id)
    if not profile:
        return [], False

    read_manga = ratings_repo.list_ratings_map(user_id)
    manga_df = _load_manga_df(db_path)

    dnr_ids = set(dnr_service.list_manga_ids(user_id))
    reading_ids = set(reading_list_service.list_manga_ids(user_id))
    exclude_ids = dnr_ids | reading_ids
    if exclude_ids:
        manga_df = manga_df[~manga_df["title_name"].isin(exclude_ids)]

    ranked, used_current = recommendation_scores(
        manga_df,
        profile,
        current_genres,
        current_themes,
        read_manga,
        top_n=limit,
        mode=mode,
        reroll=reroll,
        seed=seed,
        diversify=diversify,
        novelty=novelty,
        personalize=personalize,
        earliest_year=earliest_year,
        content_types=content_types,
    )

    if ranked is None or ranked.empty:
        return [], used_current

    language = profile.get("language") or "English"
    genre_best, theme_best = _build_rated_lookup(manga_df, read_manga, language)

    results = []
    for _, row in ranked.iterrows():
        reasons = _explain_row(row, current_genres, current_themes, profile, genre_best, theme_best)
        results.append(
            {
                "id": row.get("id"),
                "title": row.get("title_name"),
                "english_name": row.get("english_name"),
                "japanese_name": row.get("japanese_name"),
                "score": row.get("score"),
                "genres": row.get("genres"),
                "themes": row.get("themes"),
                "match_score": row.get("match_score"),
                "internal_score": row.get("internal_score"),
                "combined_score": row.get("combined_score"),
                "reasons": reasons,
            }
        )

    return results, used_current
