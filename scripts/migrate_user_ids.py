import ast
import re
import sqlite3
from pathlib import Path

DB_PATH = "/opt/manga_recommender_ml/data/db/manga.db"


def ensure_columns(conn, table):
    cur = conn.execute(f"PRAGMA table_info({table})")
    cols = {row[1] for row in cur.fetchall()}
    if "mal_id" not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN mal_id INTEGER")
    if "mdex_id" not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN mdex_id TEXT")


def backfill_table(conn, table):
    # Fill mal_id from title_name via manga_stats
    conn.execute(
        f"""
        UPDATE {table}
        SET mal_id = (
            SELECT ms.mal_id
            FROM manga_stats ms
            WHERE ms.title_name = {table}.manga_id
               OR ms.english_name = {table}.manga_id
               OR ms.japanese_name = {table}.manga_id
            LIMIT 1
        )
        WHERE mal_id IS NULL
        """
    )

    # Fill mdex_id from mal_id via map
    conn.execute(
        f"""
        UPDATE {table}
        SET mdex_id = (
            SELECT mm.mangadex_id
            FROM manga_map mm
            WHERE mm.mal_id = {table}.mal_id
            LIMIT 1
        )
        WHERE mdex_id IS NULL AND mal_id IS NOT NULL
        """
    )


def normalize_title(value):
    if not value:
        return ""
    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def normalize_item_type(value):
    if not value:
        return None
    text = str(value).strip().lower()
    mapping = {
        "manga": "manga",
        "manhwa": "manhwa",
        "manhua": "manhua",
    }
    return mapping.get(text)


def parse_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return value
    text = str(value)
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return [item.strip() for item in text.split(",") if item.strip()]


def build_title_index(conn):
    cur = conn.execute(
        """
        SELECT mal_id, title_name, english_name, japanese_name, synonymns, item_type
        FROM manga_stats
        WHERE mal_id IS NOT NULL
        """
    )
    index = {}
    stats = {}
    for row in cur.fetchall():
        mal_id = row[0]
        item_type = normalize_item_type(row[5])
        # Prefer manga/manhwa/manhua; fall back to exact matches for other types
        if row[5] and item_type is None:
            continue
        stats[mal_id] = {}
        titles = [row[1], row[2], row[3]]
        titles += parse_list(row[4])
        normalized_titles = [normalize_title(t) for t in titles if t]
        normalized_titles = [t for t in normalized_titles if t]
        # Add concatenations of jp+en if both exist
        if row[2] and row[3]:
            en = normalize_title(row[2])
            jp = normalize_title(row[3])
            if en and jp:
                normalized_titles.append(jp + en)
                normalized_titles.append(en + jp)
        for key in normalized_titles:
            index.setdefault(key, set()).add(mal_id)
    # Load stats for tie-breaking
    cur = conn.execute(
        """
        SELECT mal_id, members, scored_by, popularity, score
        FROM manga_stats
        WHERE mal_id IS NOT NULL
        """
    )
    for mal_id, members, scored_by, popularity, score in cur.fetchall():
        if mal_id in stats:
            stats[mal_id] = {
                "members": members or 0,
                "scored_by": scored_by or 0,
                "popularity": popularity or 0,
                "score": score or 0,
            }
    return index, stats


def pick_best(candidates, stats):
    best = None
    best_key = None
    for mal_id in candidates:
        meta = stats.get(mal_id, {})
        key = (
            meta.get("members", 0),
            meta.get("scored_by", 0),
            meta.get("score", 0),
            -(meta.get("popularity", 0) or 0),
        )
        if best_key is None or key > best_key:
            best_key = key
            best = mal_id
    return best


def fallback_match(manga_id, index, stats):
    key = normalize_title(manga_id)
    if not key:
        return None
    direct = index.get(key)
    if direct:
        if len(direct) == 1:
            return next(iter(direct))
        return pick_best(direct, stats)
    # Substring fallback (only if a unique candidate)
    candidates = set()
    for title_key, mal_ids in index.items():
        if not title_key:
            continue
        if title_key in key or key in title_key:
            # Require decent overlap to avoid tiny matches
            if len(title_key) >= max(6, int(len(key) * 0.7)) or len(key) >= max(6, int(len(title_key) * 0.7)):
                candidates.update(mal_ids)
    if candidates:
        if len(candidates) == 1:
            return next(iter(candidates))
        return pick_best(candidates, stats)
    return None


def backfill_table_fuzzy(conn, table, index, stats):
    cur = conn.execute(
        f"SELECT rowid, manga_id FROM {table} WHERE mal_id IS NULL"
    )
    rows = cur.fetchall()
    updates = []
    for rowid, manga_id in rows:
        mal_id = fallback_match(manga_id, index, stats)
        if mal_id:
            updates.append((mal_id, rowid))
    if updates:
        conn.executemany(
            f"UPDATE {table} SET mal_id = ? WHERE rowid = ?",
            updates,
        )
        conn.commit()


def fill_missing_mdex(conn, table):
    cur = conn.execute(
        f"SELECT rowid, mal_id FROM {table} WHERE mdex_id IS NULL AND mal_id IS NOT NULL"
    )
    rows = cur.fetchall()
    if not rows:
        return

    for rowid, mal_id in rows:
        map_row = conn.execute(
            "SELECT mangadex_id FROM manga_map WHERE mal_id = ?",
            (mal_id,),
        ).fetchone()
        if map_row:
            conn.execute(f"UPDATE {table} SET mdex_id = ? WHERE rowid = ?", (map_row[0], rowid))
            continue

        stats_row = conn.execute(
            """
            SELECT title_name, english_name, japanese_name, synonymns, item_type, volumes, chapters, status,
                   publishing_date, authors, serialization, genres, themes, demographic, description
            FROM manga_stats
            WHERE mal_id = ?
            """,
            (mal_id,),
        ).fetchone()
        if not stats_row:
            continue

        mdex_id = f"mal:{mal_id}"
        conn.execute(
            """
            INSERT OR IGNORE INTO manga_core (
                id, link, title_name, english_name, japanese_name, synonymns, item_type, volumes, chapters,
                status, publishing_date, authors, serialization, genres, themes, demographic, description,
                content_rating, original_language, cover_url, links, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mdex_id,
                None,
                stats_row[0],
                stats_row[1],
                stats_row[2],
                stats_row[3],
                stats_row[4],
                stats_row[5],
                stats_row[6],
                stats_row[7],
                stats_row[8],
                stats_row[9],
                stats_row[10],
                stats_row[11],
                stats_row[12],
                stats_row[13],
                stats_row[14],
                None,
                None,
                None,
                None,
                None,
            ),
        )
        conn.execute(
            "INSERT OR REPLACE INTO manga_map (mangadex_id, mal_id, match_method) VALUES (?, ?, ?)",
            (mdex_id, mal_id, "mal_only"),
        )
        conn.execute(f"UPDATE {table} SET mdex_id = ? WHERE rowid = ?", (mdex_id, rowid))
    conn.commit()


def report_unmatched(conn, table):
    cur = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE (mal_id IS NULL OR mdex_id IS NULL)
        """
    )
    return cur.fetchone()[0]


def main():
    if not Path(DB_PATH).exists():
        raise SystemExit(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_columns(conn, "user_ratings")
        ensure_columns(conn, "user_dnr")
        ensure_columns(conn, "user_reading_list")
        conn.commit()

        for table in ("user_ratings", "user_dnr", "user_reading_list"):
            backfill_table(conn, table)
        conn.commit()

        index, stats = build_title_index(conn)
        for table in ("user_ratings", "user_dnr", "user_reading_list"):
            backfill_table_fuzzy(conn, table, index, stats)
        conn.commit()

        for table in ("user_ratings", "user_dnr", "user_reading_list"):
            fill_missing_mdex(conn, table)

        for table in ("user_ratings", "user_dnr", "user_reading_list"):
            missing = report_unmatched(conn, table)
            print(f"{table}: {missing} rows missing mal_id or mdex_id")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
