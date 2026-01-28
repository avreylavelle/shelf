from app.db import get_db


def search_by_title(query, limit=10):
    db = get_db()
    like = f"%{query}%"
    cur = db.execute(
        """
        SELECT id, title_name, english_name, japanese_name, score, genres, themes
        FROM manga_cleaned
        WHERE title_name LIKE ? OR english_name LIKE ? OR japanese_name LIKE ?
        ORDER BY score DESC
        LIMIT ?
        """,
        (like, like, like, limit),
    )
    return cur.fetchall()


def get_by_title(title):
    db = get_db()
    cur = db.execute(
        "SELECT * FROM manga_cleaned WHERE title_name = ?",
        (title,),
    )
    return cur.fetchone()
