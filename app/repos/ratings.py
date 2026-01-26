from app.db import get_db


def list_by_user(user_id, sort="chron"):
    db = get_db()
    order_sql = "ORDER BY created_at DESC"

    if sort == "alpha":
        order_sql = "ORDER BY manga_id COLLATE NOCASE ASC"
    elif sort == "rating_desc":
        order_sql = "ORDER BY (rating IS NULL), rating DESC"
    elif sort == "rating_asc":
        order_sql = "ORDER BY (rating IS NULL), rating ASC"
    elif sort == "chron":
        order_sql = "ORDER BY created_at DESC"

    cur = db.execute(
        f"""
        SELECT user_id, manga_id, rating, created_at
        FROM user_ratings
        WHERE user_id = ?
        {order_sql}
        """,
        (user_id,),
    )
    return cur.fetchall()


def list_manga_ids_by_user(user_id):
    db = get_db()
    cur = db.execute(
        "SELECT manga_id FROM user_ratings WHERE user_id = ?",
        (user_id,),
    )
    return [row[0] for row in cur.fetchall()]


def list_ratings_map(user_id):
    db = get_db()
    cur = db.execute(
        "SELECT manga_id, rating FROM user_ratings WHERE user_id = ?",
        (user_id,),
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def upsert_rating(user_id, manga_id, rating):
    db = get_db()
    db.execute(
        """
        INSERT INTO user_ratings (user_id, manga_id, rating)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, manga_id) DO UPDATE SET rating = excluded.rating
        """,
        (user_id, manga_id, rating),
    )
    db.commit()


def delete_rating(user_id, manga_id):
    db = get_db()
    db.execute(
        "DELETE FROM user_ratings WHERE user_id = ? AND manga_id = ?",
        (user_id, manga_id),
    )
    db.commit()
