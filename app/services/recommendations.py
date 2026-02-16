import os
import sqlite3
import time

import numpy as np
import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer

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


def _extract_year_series(series):
    if series is None:
        return pd.Series(dtype="float")
    year = pd.to_numeric(series, errors="coerce")
    if year.isna().any():
        year_text = series.astype(str).str.extract(r"(19\d{2}|20\d{2})", expand=False)
        year = year.fillna(pd.to_numeric(year_text, errors="coerce"))
    return year


def _load_manga_df(db_path):
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

    # Pre-parse lists once per dataset load
    df["genres"] = df["genres"].apply(parse_list)
    df["themes"] = df["themes"].apply(parse_list)

    # Precompute published year with fallback to updated_at
    publish_year = _extract_year_series(df.get("publishing_date"))
    update_year = _extract_year_series(df.get("updated_at"))
    df["published_year"] = publish_year.fillna(update_year)

    return df


def _build_cache(db_path):
    df = _load_manga_df(db_path)
    df = df.reset_index(drop=True)

    genre_mlb = MultiLabelBinarizer()
    theme_mlb = MultiLabelBinarizer()

    genre_matrix = genre_mlb.fit_transform(df["genres"]).astype(np.uint8)
    theme_matrix = theme_mlb.fit_transform(df["themes"]).astype(np.uint8)

    genre_index = {g: i for i, g in enumerate(genre_mlb.classes_.tolist())}
    theme_index = {t: i for i, t in enumerate(theme_mlb.classes_.tolist())}

    genre_counts = genre_matrix.sum(axis=1)
    theme_counts = theme_matrix.sum(axis=1)

    id_index = {mid: idx for idx, mid in enumerate(df["id"].tolist())}
    id_to_mal = {mid: mal for mid, mal in zip(df["id"].tolist(), df["mal_id"].tolist())}

    mal_id_to_indices = {}
    for idx, mal_id in enumerate(df["mal_id"].tolist()):
        if mal_id is None or mal_id != mal_id:
            continue
        try:
            key = int(mal_id)
        except Exception:
            continue
        mal_id_to_indices.setdefault(key, []).append(idx)

    content_rating = df.get("content_rating")
    if content_rating is None:
        content_rating = pd.Series([""] * len(df))
    content_rating = content_rating.fillna("").astype(str).str.lower().to_numpy()

    nsfw_genres = [g for g in ("Hentai", "Ecchi", "Erotica") if g in genre_mlb.classes_]
    nsfw_mask = np.zeros(len(df), dtype=bool)
    if nsfw_genres:
        idxs = [genre_mlb.classes_.tolist().index(g) for g in nsfw_genres]
        nsfw_mask = np.any(genre_matrix[:, idxs] > 0, axis=1)
    nsfw_mask = nsfw_mask | np.isin(content_rating, ["erotica", "pornographic"])

    return {
        "df": df,
        "genre_mlb": genre_mlb,
        "theme_mlb": theme_mlb,
        "genre_index": genre_index,
        "theme_index": theme_index,
        "genre_matrix": genre_matrix,
        "theme_matrix": theme_matrix,
        "genre_counts": genre_counts,
        "theme_counts": theme_counts,
        "id_index": id_index,
        "id_to_mal": id_to_mal,
        "mal_id_to_indices": mal_id_to_indices,
        "published_year": df["published_year"].to_numpy(),
        "item_type": df.get("item_type").fillna("").astype(str).to_numpy(),
        "nsfw_mask": nsfw_mask,
    }


def _get_cache(db_path):
    db_path = _resolve_db_path(db_path)
    cache_ttl = int(os.environ.get("MANGA_CACHE_TTL_SEC", "21600"))
    now = time.time()
    cached = _MANGA_CACHE.get(db_path)
    if cached is not None and cache_ttl > 0:
        built_at = cached.get("built_at") or 0
        if (now - built_at) < cache_ttl:
            return cached
    elif cached is not None and cache_ttl <= 0:
        return cached
    _OPTIONS_CACHE.pop(db_path, None)
    cache = _build_cache(db_path)
    cache["built_at"] = now
    _MANGA_CACHE[db_path] = cache
    return cache


def get_available_options(db_path=None):
    db_path = _resolve_db_path(db_path)
    cached = _OPTIONS_CACHE.get(db_path)
    if cached is not None:
        return cached
    cache = _get_cache(db_path)
    manga_df = cache["df"]
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

    cache = _get_cache(db_path)
    manga_df = cache["df"]

    history_blacklist_genres = list((profile.get("blacklist_genres") or {}).keys())
    history_blacklist_themes = list((profile.get("blacklist_themes") or {}).keys())
    combined_blacklist_genres = list(dict.fromkeys((blacklist_genres or []) + history_blacklist_genres))
    combined_blacklist_themes = list(dict.fromkeys((blacklist_themes or []) + history_blacklist_themes))

    read_manga = ratings_repo.list_ratings_map(user_id)

    rated_mal_ids = set()
    if read_manga:
        # Resolve rated MAL ids to block alternate variants from showing up
        id_to_mal = cache.get("id_to_mal", {})
        for key in read_manga.keys():
            if not key:
                continue
            if str(key).startswith("mal:"):
                try:
                    rated_mal_ids.add(int(str(key).replace("mal:", "").strip()))
                except Exception:
                    pass
                continue
            mal_id = id_to_mal.get(key)
            if mal_id and mal_id == mal_id:
                try:
                    rated_mal_ids.add(int(mal_id))
                except Exception:
                    pass
        if rated_mal_ids:
            for mid in rated_mal_ids:
                for idx in cache.get("mal_id_to_indices", {}).get(mid, []):
                    try:
                        rid = manga_df.at[idx, "id"]
                    except Exception:
                        continue
                    if rid:
                        read_manga.setdefault(rid, None)

    dnr_ids = set(dnr_service.list_manga_ids(user_id))
    reading_ids = set(reading_list_service.list_manga_ids(user_id))

    total_rows = len(manga_df)
    mask = np.ones(total_rows, dtype=bool)

    # Age-based NSFW filtering
    if profile.get("age") is not None and profile["age"] < 18:
        mask &= ~cache.get("nsfw_mask", np.zeros(total_rows, dtype=bool))

    # Content type filtering
    if content_types:
        allowed = {str(t).strip() for t in content_types if str(t).strip()}
        if allowed:
            mask &= np.isin(cache.get("item_type"), list(allowed))

    # Blacklist filtering (genres/themes)
    blacklist_genres = [g for g in (combined_blacklist_genres or []) if g]
    blacklist_themes = [t for t in (combined_blacklist_themes or []) if t]
    if blacklist_genres:
        genre_index = cache.get("genre_index", {})
        idxs = [genre_index[g] for g in blacklist_genres if g in genre_index]
        if idxs:
            mask &= ~np.any(cache["genre_matrix"][:, idxs] > 0, axis=1)
    if blacklist_themes:
        theme_index = cache.get("theme_index", {})
        idxs = [theme_index[t] for t in blacklist_themes if t in theme_index]
        if idxs:
            mask &= ~np.any(cache["theme_matrix"][:, idxs] > 0, axis=1)

    # Exclude read/DNR/reading list
    exclude_ids = dnr_ids | reading_ids | set(read_manga.keys())
    id_index = cache.get("id_index", {})
    for mid in exclude_ids:
        idx = id_index.get(mid)
        if idx is not None:
            mask[idx] = False

    # Earliest year preference (filter if enough candidates remain)
    min_year = None
    try:
        min_year = int(earliest_year) if earliest_year is not None else None
    except (TypeError, ValueError):
        min_year = None
    if min_year:
        years = cache.get("published_year")
        if years is not None:
            year_mask = years >= min_year
            if year_mask.sum() >= max(limit * 5, 200):
                mask &= year_mask
        earliest_year = min_year

    row_idx = np.where(mask)[0]
    filtered_df = manga_df.iloc[row_idx].copy()

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
        blacklist_genres=combined_blacklist_genres,
        blacklist_themes=combined_blacklist_themes,
        prefiltered_df=filtered_df,
        prefiltered_idx=row_idx,
        precomputed=cache,
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
                "synonymns": row.get("synonymns"),
                "mal_id": row.get("mal_id"),
                "cover_url": row.get("cover_url"),
                "score": row.get("score"),
                "genres": row.get("genres"),
                "themes": row.get("themes"),
                "reasons": reasons,
            }
        )
    results = _diversify_reasons(results)
    return results, used_current
