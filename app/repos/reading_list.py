"""Data-access helpers for user reading-list records."""

from app.db import get_db


# Reading-list repository with canonical ID matching across mdex/MAL/raw keys.
def list_by_user(user_id, sort="chron"):
    # Sorting uses fixed SQL fragments selected from known modes.
    order_sql = "ORDER BY r.created_at DESC"
    if sort == "alpha":
        order_sql = "ORDER BY m.title_name COLLATE NOCASE ASC"
    elif sort == "chron":
        order_sql = "ORDER BY r.created_at DESC"
    db = get_db()
    # Join mapping + merged metadata so list rows can render titles/covers consistently.
    cur = db.execute(
        f"""
        SELECT r.user_id, r.manga_id, r.status, r.created_at, m.english_name, m.japanese_name, m.title_name, m.item_type, m.cover_url,
               COALESCE(r.mal_id, mm.mal_id, m.mal_id) AS mal_id,
               COALESCE(r.canonical_id, mm.mangadex_id, r.mdex_id, m.mangadex_id) AS mdex_id,
               COALESCE(r.canonical_id, mm.mangadex_id, r.mdex_id, m.mangadex_id, r.manga_id) AS canonical_id
        FROM user_reading_list r
        LEFT JOIN manga_map mm
            ON mm.mal_id = COALESCE(
                r.mal_id,
                CASE WHEN r.mdex_id LIKE 'mal:%' THEN CAST(SUBSTR(r.mdex_id, 5) AS INTEGER) END
            )
        LEFT JOIN manga_merged m
            ON m.mangadex_id = COALESCE(
                CASE WHEN r.mdex_id LIKE 'mal:%' THEN mm.mangadex_id END,
                r.mdex_id,
                r.manga_id
            )
            OR (r.mdex_id IS NULL AND m.mangadex_id = r.manga_id)
            OR (r.mdex_id IS NULL AND m.title_name = r.manga_id)
        WHERE lower(r.user_id) = lower(?)
        {order_sql}
        """,
        (user_id,),
    )
    return cur.fetchall()


def add(user_id, manga_id, status="Plan to Read", canonical_id=None, mdex_id=None, mal_id=None):
    # Remove duplicate representations before insert.
    db = get_db()
    db.execute(
        """
        DELETE FROM user_reading_list
        WHERE lower(user_id) = lower(?)
          AND (canonical_id = ? OR mdex_id = ? OR manga_id = ?)
        """,
        (user_id, canonical_id or manga_id, mdex_id or manga_id, manga_id),
    )
    db.execute(
        # `INSERT OR IGNORE` prevents duplicate PK inserts during concurrent calls.
        "INSERT OR IGNORE INTO user_reading_list (user_id, manga_id, status, mdex_id, mal_id, canonical_id) VALUES (lower(?), ?, ?, ?, ?, ?)",
        (user_id, canonical_id or manga_id, status, mdex_id, mal_id, canonical_id),
    )
    db.commit()


def remove(user_id, manga_id, canonical_id=None, mdex_id=None):
    # Delete by any known key variant for this title.
    db = get_db()
    db.execute(
        """
        DELETE FROM user_reading_list
        WHERE lower(user_id) = lower(?)
          AND (canonical_id = ? OR mdex_id = ? OR manga_id = ?)
        """,
        (user_id, canonical_id or manga_id, mdex_id or manga_id, manga_id),
    )
    db.commit()


def list_manga_ids_by_user(user_id):
    # Return normalized key list for exclusion in recommendation flow.
    db = get_db()
    cur = db.execute(
        """
        SELECT COALESCE(r.canonical_id, mm.mangadex_id, r.mdex_id, r.manga_id) AS key
        FROM user_reading_list r
        LEFT JOIN manga_map mm
            ON mm.mal_id = COALESCE(
                r.mal_id,
                CASE WHEN r.mdex_id LIKE 'mal:%' THEN CAST(SUBSTR(r.mdex_id, 5) AS INTEGER) END
            )
        WHERE lower(r.user_id) = lower(?)
        """,
        (user_id,),
    )
    # Ignore null keys so callers can safely build a set().
    return [row[0] for row in cur.fetchall() if row[0]]


def update_status(user_id, manga_id, status, canonical_id=None, mdex_id=None, mal_id=None):
    # Update status and backfill IDs if a better key is now available.
    db = get_db()
    db.execute(
        """
        UPDATE user_reading_list
        -- Preserve existing mal_id/canonical_id when already populated.
        SET status = ?, mdex_id = ?, mal_id = COALESCE(mal_id, ?), canonical_id = COALESCE(canonical_id, ?)
        WHERE lower(user_id) = lower(?)
          AND (canonical_id = ? OR mdex_id = ? OR manga_id = ?)
        """,
        (
            status,
            mdex_id or manga_id,
            mal_id,
            canonical_id,
            user_id,
            canonical_id or manga_id,
            mdex_id or manga_id,
            manga_id,
        ),
    )
    db.commit()
