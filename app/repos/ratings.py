from app.db import get_db


def list_by_user(user_id, sort="chron"):
    db = get_db()
    order_sql = "ORDER BY r.created_at DESC"

    if sort == "alpha":
        order_sql = "ORDER BY r.manga_id COLLATE NOCASE ASC"
    elif sort == "rating_desc":
        order_sql = "ORDER BY (r.rating IS NULL), r.rating DESC"
    elif sort == "rating_asc":
        order_sql = "ORDER BY (r.rating IS NULL), r.rating ASC"
    elif sort == "chron":
        order_sql = "ORDER BY r.created_at DESC"

    cur = db.execute(
        f"""
        SELECT r.user_id, r.manga_id, r.rating, r.recommended_by_us, r.finished_reading, r.created_at,
               m.title_name, m.english_name, m.japanese_name, m.item_type, m.cover_url, m.mal_id,
               COALESCE(r.mdex_id, m.mangadex_id) AS mdex_id
        FROM user_ratings r
        LEFT JOIN manga_merged m
            ON m.mangadex_id = r.mdex_id
            OR (r.mdex_id IS NULL AND m.mangadex_id = r.manga_id)
            OR (r.mdex_id IS NULL AND m.title_name = r.manga_id)
        WHERE lower(r.user_id) = lower(?)
        {order_sql}
        """,
        (user_id,),
    )
    return cur.fetchall()


def list_ratings_map(user_id):
    db = get_db()
    cur = db.execute(
        """
        SELECT COALESCE(r.mdex_id, m.mangadex_id, r.manga_id) AS key, r.rating
        FROM user_ratings r
        LEFT JOIN manga_merged m
            ON m.mangadex_id = r.mdex_id
            OR (r.mdex_id IS NULL AND m.mangadex_id = r.manga_id)
            OR (r.mdex_id IS NULL AND m.title_name = r.manga_id)
        WHERE lower(r.user_id) = lower(?)
        """,
        (user_id,),
    )
    return {row[0]: row[1] for row in cur.fetchall() if row[0]}


def upsert_rating(user_id, manga_id, rating, recommended_by_us, finished_reading):
    db = get_db()
    existing = db.execute(
        """
        SELECT manga_id
        FROM user_ratings
        WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)
        """,
        (user_id, manga_id, manga_id),
    ).fetchone()
    key = existing[0] if existing else manga_id
    db.execute(
        """
        INSERT INTO user_ratings (user_id, manga_id, rating, recommended_by_us, finished_reading, mdex_id)
        VALUES (lower(?), ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, manga_id) DO UPDATE SET
            rating = excluded.rating,
            recommended_by_us = excluded.recommended_by_us,
            finished_reading = excluded.finished_reading,
            mdex_id = excluded.mdex_id
        """,
        (user_id, key, rating, recommended_by_us, finished_reading, manga_id),
    )
    db.commit()


def delete_rating(user_id, manga_id):
    db = get_db()
    db.execute(
        "DELETE FROM user_ratings WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (user_id, manga_id, manga_id),
    )
    db.commit()

def get_rating_value(user_id, manga_id):
    db = get_db()
    cur = db.execute(
        "SELECT rating FROM user_ratings WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (user_id, manga_id, manga_id),
    )
    row = cur.fetchone()
    return row[0] if row else None
