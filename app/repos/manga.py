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


def top_by_score_excluding(exclude_titles, limit=20):
    db = get_db()
    placeholders = ",".join(["?"] * len(exclude_titles))
    if exclude_titles:
        sql = (
            "SELECT id, title_name, english_name, japanese_name, score, genres, themes "
            "FROM manga_cleaned "
            f"WHERE title_name NOT IN ({placeholders}) "
            "ORDER BY score DESC "
            "LIMIT ?"
        )
        params = [*exclude_titles, limit]
    else:
        # fallback if no exclude list
        sql = (
            "SELECT id, title_name, english_name, japanese_name, score, genres, themes "
            "FROM manga_cleaned "
            "ORDER BY score DESC "
            "LIMIT ?"
        )
        params = [limit]
    cur = db.execute(sql, params)
    return cur.fetchall()
