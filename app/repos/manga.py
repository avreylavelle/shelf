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
               synonymns,
               cover_url,
               score,
               genres,
               themes,
               item_type
        FROM manga_merged
        WHERE (title_name LIKE ? OR english_name LIKE ? OR japanese_name LIKE ? OR synonymns LIKE ?)
          AND mangadex_id NOT LIKE 'mal:%'
        ORDER BY score IS NULL, score DESC
        LIMIT ?
        """,
        (like, like, like, like, limit),
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


def resolve_manga_ref(manga_id):
    raw = (manga_id or "").strip()
    if not raw:
        return {"raw": raw, "canonical_id": None, "mdex_id": None, "mal_id": None}

    db = get_db()

    if raw.lower().startswith("mal:"):
        mal_text = raw.split(":", 1)[-1].strip()
        try:
            mal_id = int(mal_text)
        except (TypeError, ValueError):
            mal_id = None
        mdex_id = None
        if mal_id is not None:
            row = db.execute("SELECT mangadex_id FROM manga_map WHERE mal_id = ?", (mal_id,)).fetchone()
            if row:
                mdex_id = row["mangadex_id"]
        canonical = mdex_id or (f"mal:{mal_id}" if mal_id is not None else raw)
        return {"raw": raw, "canonical_id": canonical, "mdex_id": mdex_id, "mal_id": mal_id}

    row = db.execute(
        "SELECT mangadex_id, mal_id FROM manga_merged WHERE mangadex_id = ?",
        (raw,),
    ).fetchone()
    if row:
        return {
            "raw": raw,
            "canonical_id": row["mangadex_id"],
            "mdex_id": row["mangadex_id"],
            "mal_id": row["mal_id"],
        }

    rows = db.execute(
        """
        SELECT mangadex_id, mal_id
        FROM manga_merged
        WHERE title_name = ? OR english_name = ? OR japanese_name = ?
        LIMIT 2
        """,
        (raw, raw, raw),
    ).fetchall()
    if len(rows) == 1:
        row = rows[0]
        return {
            "raw": raw,
            "canonical_id": row["mangadex_id"],
            "mdex_id": row["mangadex_id"],
            "mal_id": row["mal_id"],
        }

    rows = db.execute(
        """
        SELECT mal_id
        FROM manga_stats
        WHERE title_name = ? OR english_name = ? OR japanese_name = ?
        LIMIT 2
        """,
        (raw, raw, raw),
    ).fetchall()
    if len(rows) == 1:
        mal_id = rows[0]["mal_id"]
        mdex_id = None
        if mal_id is not None:
            row = db.execute("SELECT mangadex_id FROM manga_map WHERE mal_id = ?", (mal_id,)).fetchone()
            if row:
                mdex_id = row["mangadex_id"]
        canonical = mdex_id or f"mal:{mal_id}"
        return {"raw": raw, "canonical_id": canonical, "mdex_id": mdex_id, "mal_id": mal_id}

    return {"raw": raw, "canonical_id": raw, "mdex_id": None, "mal_id": None}
