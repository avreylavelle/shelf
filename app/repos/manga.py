from app.db import get_db


def search_by_title(query, limit=10):
    db = get_db()
    like = f"%{query}%"
    cur = db.execute(
        """
        SELECT id, title_name, score, genres, themes
        FROM manga_cleaned
        WHERE title_name LIKE ?
        ORDER BY score DESC
        LIMIT ?
        """,
        (like, limit),
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
            "SELECT id, title_name, score, genres, themes "
            "FROM manga_cleaned "
            f"WHERE title_name NOT IN ({placeholders}) "
            "ORDER BY score DESC "
            "LIMIT ?"
        )
        params = [*exclude_titles, limit]
    else:
        sql = (
            "SELECT id, title_name, score, genres, themes "
            "FROM manga_cleaned "
            "ORDER BY score DESC "
            "LIMIT ?"
        )
        params = [limit]
    cur = db.execute(sql, params)
    return cur.fetchall()
