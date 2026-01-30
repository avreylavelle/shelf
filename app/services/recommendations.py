import os
import sqlite3

import pandas as pd

from app.repos import profile as profile_repo
from app.repos import ratings as ratings_repo
from app.repos import manga as manga_repo
from app.services import dnr as dnr_service
from app.services import reading_list as reading_list_service
from recommender.recommender import recommendation_scores
from utils.lookup import get_all_unique
from utils.parsing import parse_list

_MANGA_CACHE = {}
_OPTIONS_CACHE = {}
_STATS_NAME_CACHE = {}


def _english_like(value):
    if not value:
        return False
    latin = 0
    nonlatin = 0
    for ch in str(value):
        if ch.isalpha():
            if ord(ch) < 128:
                latin += 1
            else:
                nonlatin += 1
    return latin > 0 and nonlatin == 0


def _stats_english_name(mal_id):
    if not mal_id:
        return None
    try:
        mal_id = int(mal_id)
    except Exception:
        return None
    cached = _STATS_NAME_CACHE.get(mal_id)
    if cached is not None:
        return cached
    row = manga_repo.get_stats_by_mal_id(mal_id)
    name = None
    if row:
        try:
            name = row.get("english_name")
        except AttributeError:
            name = row["english_name"] if "english_name" in row.keys() else None
    _STATS_NAME_CACHE[mal_id] = name
    return name


def _best_synonym(row, title):
    synonyms = parse_list(row.get("synonymns"))
    if not synonyms:
        return None
    for raw in synonyms:
        candidate = str(raw).strip()
        if not candidate:
            continue
        if candidate.strip().lower() == (title or "").strip().lower():
            continue
        if _english_like(candidate):
            return candidate
    return None


def _display_title_for_row(row, language):
    title = row.get("title_name") or row.get("english_name") or row.get("japanese_name") or ""
    if language == "Japanese":
        return row.get("japanese_name") or title
    english = row.get("english_name")
    if english and str(english).strip().lower() != str(title).strip().lower():
        return english
    stats_name = _stats_english_name(row.get("mal_id"))
    if stats_name:
        return stats_name
    synonym = _best_synonym(row, title)
    if synonym:
        return synonym
    return english or title


def _build_rated_lookup(manga_df, read_manga, language):
    if manga_df is None or manga_df.empty or not read_manga:
        return {}, {}
    genre_best = {}
    theme_best = {}
    for manga_id, rating in read_manga.items():
        if rating is None:
            continue
        try:
            rating_value = float(rating)
        except (TypeError, ValueError):
            continue
        if rating_value <= 0:
            continue
        try:
            matches = manga_df[manga_df["id"] == manga_id]
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
                genre_best[g] = (display_title or manga_id, rating_value)
        for t in themes:
            current = theme_best.get(t)
            if current is None or rating_value > current[1]:
                theme_best[t] = (display_title or manga_id, rating_value)
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
        reasons.append(f"Similar to {title} (rated {rating:.1f})")

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


def _diversify_reasons(results, max_title_reasons=2):
    if not results:
        return results
    used_titles = {}
    title_reason_count = 0
    replacements = [
        "Matches your favorites",
        "Aligns with your highly rated history",
        "Fits your past ratings",
    ]
    alt_idx = 0
    for item in results:
        reasons = item.get("reasons") or []
        new_reasons = []
        for reason in reasons:
            if reason.startswith("Similar to "):
                title = reason[len("Similar to ") :].split(" (rated", 1)[0].strip()
                seen = used_titles.get(title, 0)
                if title_reason_count >= max_title_reasons or seen >= 1:
                    reason = replacements[alt_idx % len(replacements)]
                    alt_idx += 1
                else:
                    used_titles[title] = seen + 1
                    title_reason_count += 1
            new_reasons.append(reason)
        item["reasons"] = new_reasons
    return results


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
        df = pd.read_sql_query(
            """
            SELECT
                mangadex_id AS id,
                mangadex_id,
                title_name,
                english_name,
                japanese_name,
                synonymns,
                item_type,
                volumes,
                chapters,
                status,
                publishing_date,
                authors,
                serialization,
                genres,
                themes,
                demographic,
                description,
                content_rating,
                original_language,
                cover_url,
                links,
                updated_at,
                mal_id,
                score,
                scored_by,
                ranked,
                popularity,
                members,
                favorited
            FROM manga_merged
            WHERE mangadex_id NOT LIKE 'mal:%'
            """,
            conn,
        )
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


def recommend_for_user(db_path, user_id, current_genres, current_themes, limit=20, mode=None, reroll=False, seed=None, diversify=True, novelty=False, personalize=True, earliest_year=None, content_types=None, blacklist_genres=None, blacklist_themes=None):
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
        manga_df = manga_df[~manga_df["id"].isin(exclude_ids)]

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
        blacklist_genres=blacklist_genres,
        blacklist_themes=blacklist_themes,
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
                "cover_url": row.get("cover_url"),
                "score": row.get("score"),
                "genres": row.get("genres"),
                "themes": row.get("themes"),
                "reasons": reasons,
            }
        )
    results = _diversify_reasons(results)
    return results, used_current
