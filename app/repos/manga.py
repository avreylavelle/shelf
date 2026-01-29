from app.db import get_db


def search_by_title(query, limit=10):
    db = get_db()
    like = f"%{query}%"
    cur = db.execute(
        """
        SELECT mangadex_id AS id,
               mal_id,
               title_name,
               english_name,
               japanese_name,
               cover_url,
               score,
               genres,
               themes,
               item_type
        FROM manga_merged
        WHERE (title_name LIKE ? OR english_name LIKE ? OR japanese_name LIKE ?)
          AND mangadex_id NOT LIKE 'mal:%'
        ORDER BY score IS NULL, score DESC
        LIMIT ?
        """,
        (like, like, like, limit),
    )
    return cur.fetchall()


def get_by_id(mangadex_id):
    db = get_db()
    cur = db.execute(
        "SELECT * FROM manga_merged WHERE mangadex_id = ?",
        (mangadex_id,),
    )
    return cur.fetchone()


def get_by_title(title):
    db = get_db()
    cur = db.execute(
        """
        SELECT * FROM manga_merged
        WHERE title_name = ? OR english_name = ? OR japanese_name = ?
        """,
        (title, title, title),
    )
    return cur.fetchone()


def get_stats_by_mal_id(mal_id):
    db = get_db()
    cur = db.execute(
        """
        SELECT *
        FROM manga_stats
        WHERE mal_id = ?
        """,
        (mal_id,),
    )
    return cur.fetchone()


def get_stats_by_title(title):
    db = get_db()
    cur = db.execute(
        """
        SELECT *
        FROM manga_stats
        WHERE title_name = ? OR english_name = ? OR japanese_name = ?
        """,
        (title, title, title),
    )
    return cur.fetchone()
