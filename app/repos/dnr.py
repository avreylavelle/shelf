from app.db import get_db


def list_by_user(user_id, sort="chron"):
    order_sql = "ORDER BY d.created_at DESC"
    if sort == "alpha":
        order_sql = "ORDER BY m.title_name COLLATE NOCASE ASC"
    elif sort == "chron":
        order_sql = "ORDER BY d.created_at DESC"
    db = get_db()
    cur = db.execute(
        f"""
        SELECT d.user_id, d.manga_id, d.created_at, m.english_name, m.japanese_name, m.title_name, m.item_type, m.cover_url,
               COALESCE(d.mal_id, mm.mal_id, m.mal_id) AS mal_id,
               COALESCE(mm.mangadex_id, d.mdex_id, m.mangadex_id) AS mdex_id
        FROM user_dnr d
        LEFT JOIN manga_map mm
            ON mm.mal_id = COALESCE(
                d.mal_id,
                CASE WHEN d.mdex_id LIKE 'mal:%' THEN CAST(SUBSTR(d.mdex_id, 5) AS INTEGER) END
            )
        LEFT JOIN manga_merged m
            ON m.mangadex_id = COALESCE(
                CASE WHEN d.mdex_id LIKE 'mal:%' THEN mm.mangadex_id END,
                d.mdex_id,
                d.manga_id
            )
            OR (d.mdex_id IS NULL AND m.mangadex_id = d.manga_id)
            OR (d.mdex_id IS NULL AND m.title_name = d.manga_id)
        WHERE lower(d.user_id) = lower(?)
        {order_sql}
        """,
        (user_id,),
    )
    return cur.fetchall()


def add(user_id, manga_id):
    db = get_db()
    db.execute(
        "DELETE FROM user_dnr WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (user_id, manga_id, manga_id),
    )
    db.execute(
        "INSERT OR IGNORE INTO user_dnr (user_id, manga_id, mdex_id) VALUES (lower(?), ?, ?)",
        (user_id, manga_id, manga_id),
    )
    db.commit()


def remove(user_id, manga_id):
    db = get_db()
    db.execute(
        "DELETE FROM user_dnr WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (user_id, manga_id, manga_id),
    )
    db.commit()


def list_manga_ids_by_user(user_id):
    db = get_db()
    cur = db.execute(
        """
        SELECT COALESCE(mm.mangadex_id, d.mdex_id, d.manga_id) AS key
        FROM user_dnr d
        LEFT JOIN manga_map mm
            ON mm.mal_id = COALESCE(
                d.mal_id,
                CASE WHEN d.mdex_id LIKE 'mal:%' THEN CAST(SUBSTR(d.mdex_id, 5) AS INTEGER) END
            )
        WHERE lower(d.user_id) = lower(?)
        """,
        (user_id,),
    )
    return [row[0] for row in cur.fetchall() if row[0]]
