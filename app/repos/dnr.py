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
        SELECT d.user_id, d.manga_id, d.created_at, m.english_name, m.japanese_name, m.title_name, m.item_type
        FROM user_dnr d
        LEFT JOIN (
            SELECT title_name,
                   MIN(english_name) AS english_name,
                   MIN(japanese_name) AS japanese_name,
                   MIN(item_type) AS item_type
            FROM manga_cleaned
            GROUP BY title_name
        ) m ON m.title_name = d.manga_id
        WHERE lower(d.user_id) = lower(?)
        {order_sql}
        """,
        (user_id,),
    )
    return cur.fetchall()


def add(user_id, manga_id):
    db = get_db()
    db.execute(
        "INSERT OR IGNORE INTO user_dnr (user_id, manga_id) VALUES (lower(?), ?)",
        (user_id, manga_id),
    )
    db.commit()


def remove(user_id, manga_id):
    db = get_db()
    db.execute("DELETE FROM user_dnr WHERE lower(user_id) = lower(?) AND manga_id = ?", (user_id, manga_id))
    db.commit()


def list_manga_ids_by_user(user_id):
    db = get_db()
    cur = db.execute("SELECT manga_id FROM user_dnr WHERE lower(user_id) = lower(?)", (user_id,))
    return [row[0] for row in cur.fetchall()]
