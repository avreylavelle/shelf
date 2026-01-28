import os
import sqlite3

from app.db import get_db
from app.services import profile as profile_service
from utils.parsing import parse_list

CLICK_WEIGHT = 0.1
READING_WEIGHT = 0.05
READING_IN_PROGRESS_WEIGHT = 0.15
DNR_WEIGHT = -0.8
FINISHED_BONUS = 0.3
RECOMMENDED_MULTIPLIER = 1.05


def _resolve_db_path(db_path):
    if db_path:
        db_path = os.path.expandvars(os.path.expanduser(db_path))
        if not os.path.isabs(db_path):
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            db_path = os.path.join(base_dir, db_path)
        return os.path.abspath(db_path)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    return os.path.join(base_dir, "data", "db", "manga.db")


def record_event(user_id, event_type, manga_id=None, value=None):
    db = get_db()
    db.execute(
        "INSERT INTO user_events (user_id, manga_id, event_type, event_value) VALUES (?, ?, ?, ?)",
        (user_id, manga_id, event_type, value),
    )
    db.commit()


def _fetch_manga_tags(db_path, manga_ids):
    ids = [mid for mid in set(manga_ids) if mid]
    if not ids:
        return {}
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        results = {}
        chunk_size = 900
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i : i + chunk_size]
            placeholders = ",".join(["?"] * len(chunk))
            query = f"SELECT title_name, genres, themes FROM manga_cleaned WHERE title_name IN ({placeholders})"
            for row in conn.execute(query, chunk):
                results[row["title_name"]] = {
                    "genres": parse_list(row["genres"]),
                    "themes": parse_list(row["themes"]),
                }
        return results
    finally:
        conn.close()


def _add_scores(target, tags, weight):
    if not tags:
        return
    per = weight / max(len(tags), 1)
    for tag in tags:
        target[tag] = target.get(tag, 0) + per


def _normalize(weights):
    denom = sum(abs(v) for v in weights.values())
    if denom <= 0:
        return {}
    return {k: v / denom for k, v in weights.items()}


def recompute_affinities(user_id, db_path=None):
    db_path = _resolve_db_path(db_path)
    db = get_db()

    ratings = db.execute(
        "SELECT manga_id, rating, recommended_by_us, finished_reading FROM user_ratings WHERE lower(user_id) = lower(?)",
        (user_id,),
    ).fetchall()
    dnr_rows = db.execute(
        "SELECT manga_id FROM user_dnr WHERE lower(user_id) = lower(?)",
        (user_id,),
    ).fetchall()
    reading_rows = db.execute(
        "SELECT manga_id, status FROM user_reading_list WHERE lower(user_id) = lower(?)",
        (user_id,),
    ).fetchall()
    clicked_rows = db.execute(
        "SELECT DISTINCT manga_id FROM user_events WHERE lower(user_id) = lower(?) AND event_type = 'clicked' AND manga_id IS NOT NULL",
        (user_id,),
    ).fetchall()

    manga_ids = [row["manga_id"] for row in ratings]
    manga_ids += [row["manga_id"] for row in dnr_rows]
    manga_ids += [row["manga_id"] for row in reading_rows]
    manga_ids += [row["manga_id"] for row in clicked_rows]

    tag_map = _fetch_manga_tags(db_path, manga_ids)

    genre_scores = {}
    theme_scores = {}

    for row in ratings:
        manga_id = row["manga_id"]
        tag_info = tag_map.get(manga_id)
        if not tag_info:
            continue
        rating = row["rating"]
        if rating is None:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue
        base = (rating_value - 5) / 5
        if row["recommended_by_us"]:
            base *= RECOMMENDED_MULTIPLIER
        _add_scores(genre_scores, tag_info["genres"], base)
        _add_scores(theme_scores, tag_info["themes"], base)
        if row["finished_reading"]:
            _add_scores(genre_scores, tag_info["genres"], FINISHED_BONUS)
            _add_scores(theme_scores, tag_info["themes"], FINISHED_BONUS)

    for row in dnr_rows:
        manga_id = row["manga_id"]
        tag_info = tag_map.get(manga_id)
        if not tag_info:
            continue
        _add_scores(genre_scores, tag_info["genres"], DNR_WEIGHT)
        _add_scores(theme_scores, tag_info["themes"], DNR_WEIGHT)

    for row in reading_rows:
        manga_id = row["manga_id"]
        tag_info = tag_map.get(manga_id)
        if not tag_info:
            continue
        status = (row["status"] or "").strip().lower()
        weight = READING_IN_PROGRESS_WEIGHT if status == "in progress" else READING_WEIGHT
        _add_scores(genre_scores, tag_info["genres"], weight)
        _add_scores(theme_scores, tag_info["themes"], weight)

    for row in clicked_rows:
        manga_id = row["manga_id"]
        tag_info = tag_map.get(manga_id)
        if not tag_info:
            continue
        _add_scores(genre_scores, tag_info["genres"], CLICK_WEIGHT)
        _add_scores(theme_scores, tag_info["themes"], CLICK_WEIGHT)

    norm_genres = _normalize(genre_scores)
    norm_themes = _normalize(theme_scores)

    profile_service.set_signal_affinities(user_id, norm_genres, norm_themes)
    return norm_genres, norm_themes


def get_event_counts(user_id):
    db = get_db()
    rows = db.execute(
        "SELECT event_type, COUNT(*) AS count FROM user_events WHERE lower(user_id) = lower(?) GROUP BY event_type",
        (user_id,),
    ).fetchall()
    return {row["event_type"]: row["count"] for row in rows}


def get_snapshot(user_id):
    db = get_db()
    ratings_count = db.execute(
        "SELECT COUNT(*) AS count FROM user_ratings WHERE lower(user_id) = lower(?) AND rating IS NOT NULL",
        (user_id,),
    ).fetchone()["count"]
    profile = profile_service.get_profile(user_id) or {}

    def top_items(items, limit=10):
        return sorted(items.items(), key=lambda kv: abs(kv[1]), reverse=True)[:limit]

    return {
        "user_id": profile.get("username") or user_id,
        "ratings_count": ratings_count,
        "signal_genres": top_items(profile.get("signal_genres", {})),
        "signal_themes": top_items(profile.get("signal_themes", {})),
        "preferred_genres": top_items(profile.get("preferred_genres", {})),
        "preferred_themes": top_items(profile.get("preferred_themes", {})),
        "event_counts": get_event_counts(user_id),
    }
