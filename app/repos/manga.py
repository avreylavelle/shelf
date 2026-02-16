"""Data-access helpers for manga search and identifier resolution."""

from app.db import get_db


# Read-only lookup helpers for manga/title resolution.
def search_by_title(query, limit=10):
    # Broad match for UI search against common title fields.
    db = get_db()
    # Wrap in '%' so SQLite LIKE matches anywhere in the field.
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
          -- Exclude stats-only pseudo rows; UI actions expect mdex-backed IDs.
          AND mangadex_id NOT LIKE 'mal:%'
        -- Push unrated rows down while still returning them if needed.
        ORDER BY score IS NULL, score DESC
        LIMIT ?
        """,
        (like, like, like, like, limit),
    )
    return cur.fetchall()


def get_by_id(mangadex_id):
    # Primary details lookup from merged metadata view.
    db = get_db()
    cur = db.execute(
        "SELECT * FROM manga_merged WHERE mangadex_id = ?",
        (mangadex_id,),
    )
    return cur.fetchone()


def get_by_title(title):
    # Exact title fallback when an ID is not available.
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
    # Read raw MAL stats row for a specific MAL ID.
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
    # Exact title fallback in stats-only table.
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
    # Normalize mixed user input (mdex ID, "mal:<id>", or title) to canonical refs.
    raw = (manga_id or "").strip()
    if not raw:
        return {"raw": raw, "canonical_id": None, "mdex_id": None, "mal_id": None}

    db = get_db()

    if raw.lower().startswith("mal:"):
        # Input is explicitly a MAL key.
        mal_text = raw.split(":", 1)[-1].strip()
        try:
            mal_id = int(mal_text)
        except (TypeError, ValueError):
            mal_id = None
        mdex_id = None
        if mal_id is not None:
            # Try to map MAL -> MangaDex so downstream storage can share one key.
            row = db.execute("SELECT mangadex_id FROM manga_map WHERE mal_id = ?", (mal_id,)).fetchone()
            if row:
                mdex_id = row["mangadex_id"]
        canonical = mdex_id or (f"mal:{mal_id}" if mal_id is not None else raw)
        return {"raw": raw, "canonical_id": canonical, "mdex_id": mdex_id, "mal_id": mal_id}

    # Input might already be a MangaDex ID.
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

    # If title maps to exactly one merged row, treat it as canonical.
    rows = db.execute(
        """
        SELECT mangadex_id, mal_id
        FROM manga_merged
        WHERE title_name = ? OR english_name = ? OR japanese_name = ?
        -- Fetch at most 2 so we can cheaply detect ambiguity.
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

    # As a final structured fallback, try unique MAL stats match.
    rows = db.execute(
        """
        SELECT mal_id
        FROM manga_stats
        WHERE title_name = ? OR english_name = ? OR japanese_name = ?
        -- Same ambiguity check as above.
        LIMIT 2
        """,
        (raw, raw, raw),
    ).fetchall()
    if len(rows) == 1:
        mal_id = rows[0]["mal_id"]
        mdex_id = None
        if mal_id is not None:
            # If a map exists, prefer mdex as canonical; otherwise keep mal:<id>.
            row = db.execute("SELECT mangadex_id FROM manga_map WHERE mal_id = ?", (mal_id,)).fetchone()
            if row:
                mdex_id = row["mangadex_id"]
        canonical = mdex_id or f"mal:{mal_id}"
        return {"raw": raw, "canonical_id": canonical, "mdex_id": mdex_id, "mal_id": mal_id}

    # Unknown/ambiguous input: preserve raw value so callers can still store it.
    return {"raw": raw, "canonical_id": raw, "mdex_id": None, "mal_id": None}
