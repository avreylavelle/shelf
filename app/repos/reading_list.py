from app.db import get_db


def list_by_user(user_id, sort="chron"):
    order_sql = "ORDER BY r.created_at DESC"
    if sort == "alpha":
        order_sql = "ORDER BY m.title_name COLLATE NOCASE ASC"
    elif sort == "chron":
        order_sql = "ORDER BY r.created_at DESC"
    db = get_db()
    cur = db.execute(
        f"""
        SELECT r.user_id, r.manga_id, r.status, r.created_at, m.english_name, m.japanese_name, m.title_name, m.item_type,
               COALESCE(r.mdex_id, m.mangadex_id) AS mdex_id
        FROM user_reading_list r
        LEFT JOIN manga_merged m
            ON m.mangadex_id = r.mdex_id
            OR (r.mdex_id IS NULL AND m.title_name = r.manga_id)
        WHERE lower(r.user_id) = lower(?)
        {order_sql}
        """,
        (user_id,),
    )
    return cur.fetchall()


def add(user_id, manga_id, status="Plan to Read"):
    db = get_db()
    db.execute(
        "DELETE FROM user_reading_list WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (user_id, manga_id, manga_id),
    )
    db.execute(
        "INSERT OR IGNORE INTO user_reading_list (user_id, manga_id, status, mdex_id) VALUES (lower(?), ?, ?, ?)",
        (user_id, manga_id, status, manga_id),
    )
    db.commit()


def remove(user_id, manga_id):
    db = get_db()
    db.execute(
        "DELETE FROM user_reading_list WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (user_id, manga_id, manga_id),
    )
    db.commit()


def list_manga_ids_by_user(user_id):
    db = get_db()
    cur = db.execute(
        "SELECT COALESCE(mdex_id, manga_id) AS key FROM user_reading_list WHERE lower(user_id) = lower(?)",
        (user_id,),
    )
    return [row[0] for row in cur.fetchall() if row[0]]


def update_status(user_id, manga_id, status):
    db = get_db()
    db.execute(
        "UPDATE user_reading_list SET status = ?, mdex_id = ? WHERE lower(user_id) = lower(?) AND (mdex_id = ? OR manga_id = ?)",
        (status, manga_id, user_id, manga_id, manga_id),
    )
    db.commit()
