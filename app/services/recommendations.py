import os
import sqlite3

import pandas as pd

from app.repos import profile as profile_repo
from app.repos import ratings as ratings_repo
from app.services import dnr as dnr_service
from app.services import reading_list as reading_list_service
from recommender.recommender import recommendation_scores
from utils.lookup import get_all_unique

_MANGA_CACHE = {}
_OPTIONS_CACHE = {}


def _resolve_db_path(db_path):
    if db_path:
        db_path = os.path.expandvars(os.path.expanduser(db_path))
        if not os.path.isabs(db_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            db_path = os.path.join(base_dir, db_path)
        return os.path.abspath(db_path)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "Dataset", "manga.db")


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


def recommend_for_user(db_path, user_id, current_genres, current_themes, limit=20, update_profile=True, mode=None, reroll=False, seed=None):
    db_path = _resolve_db_path(db_path)
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
        manga_df, profile, current_genres, current_themes, read_manga, top_n=limit, mode=mode, reroll=reroll, seed=seed
    )

    if ranked is None or ranked.empty:
        return [], used_current

    results = []
    for _, row in ranked.iterrows():
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
            }
        )

    return results, used_current
