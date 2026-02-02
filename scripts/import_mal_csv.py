import argparse
import csv
import os
import sqlite3
from pathlib import Path


def ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manga_stats (
            mal_id INTEGER PRIMARY KEY,
            link TEXT,
            title_name TEXT,
            score REAL,
            scored_by REAL,
            ranked REAL,
            popularity REAL,
            members REAL,
            favorited REAL,
            synonymns TEXT,
            japanese_name TEXT,
            english_name TEXT,
            german_name TEXT,
            french_name TEXT,
            spanish_name TEXT,
            item_type TEXT,
            volumes TEXT,
            chapters TEXT,
            status TEXT,
            publishing_date TEXT,
            authors TEXT,
            serialization TEXT,
            genres TEXT,
            themes TEXT,
            demographic TEXT,
            description TEXT,
            background TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_stats_title ON manga_stats (title_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_stats_english ON manga_stats (english_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_stats_japanese ON manga_stats (japanese_name)")


def clean(value):
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped != "" else None
    return value


def main():
    parser = argparse.ArgumentParser(description="Import MAL CSV into manga_stats table")
    parser.add_argument("--db", default="/opt/shelf/data/db/manga.db")
    parser.add_argument("--csv", default="/opt/shelf/data/imports/mal.csv")
    parser.add_argument("--replace", action="store_true", help="replace existing manga_stats rows")
    parser.add_argument("--chunk", type=int, default=2000)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")

    conn = sqlite3.connect(args.db)
    try:
        ensure_tables(conn)
        if args.replace:
            conn.execute("DELETE FROM manga_stats")
            conn.commit()

        with csv_path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            expected = [
                "id",
                "link",
                "title_name",
                "score",
                "scored_by",
                "ranked",
                "popularity",
                "members",
                "favorited",
                "synonymns",
                "japanese_name",
                "english_name",
                "german_name",
                "french_name",
                "spanish_name",
                "item_type",
                "volumes",
                "chapters",
                "status",
                "publishing_date",
                "authors",
                "serialization",
                "genres",
                "themes",
                "demographic",
                "description",
                "background",
            ]
            missing = [col for col in expected if col not in reader.fieldnames]
            if missing:
                raise SystemExit(f"CSV missing columns: {missing}")

            rows = []
            for row in reader:
                values = [
                    clean(row.get("id")),
                    clean(row.get("link")),
                    clean(row.get("title_name")),
                    clean(row.get("score")),
                    clean(row.get("scored_by")),
                    clean(row.get("ranked")),
                    clean(row.get("popularity")),
                    clean(row.get("members")),
                    clean(row.get("favorited")),
                    clean(row.get("synonymns")),
                    clean(row.get("japanese_name")),
                    clean(row.get("english_name")),
                    clean(row.get("german_name")),
                    clean(row.get("french_name")),
                    clean(row.get("spanish_name")),
                    clean(row.get("item_type")),
                    clean(row.get("volumes")),
                    clean(row.get("chapters")),
                    clean(row.get("status")),
                    clean(row.get("publishing_date")),
                    clean(row.get("authors")),
                    clean(row.get("serialization")),
                    clean(row.get("genres")),
                    clean(row.get("themes")),
                    clean(row.get("demographic")),
                    clean(row.get("description")),
                    clean(row.get("background")),
                ]
                rows.append(values)
                if len(rows) >= args.chunk:
                    conn.executemany(
                        """
                        INSERT OR REPLACE INTO manga_stats (
                            mal_id, link, title_name, score, scored_by, ranked, popularity, members, favorited,
                            synonymns, japanese_name, english_name, german_name, french_name, spanish_name,
                            item_type, volumes, chapters, status, publishing_date, authors, serialization,
                            genres, themes, demographic, description, background
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
                    conn.commit()
                    rows = []
            if rows:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO manga_stats (
                        mal_id, link, title_name, score, scored_by, ranked, popularity, members, favorited,
                        synonymns, japanese_name, english_name, german_name, french_name, spanish_name,
                        item_type, volumes, chapters, status, publishing_date, authors, serialization,
                        genres, themes, demographic, description, background
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows,
                )
                conn.commit()

        conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_stats_title ON manga_stats (title_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_stats_english ON manga_stats (english_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_stats_japanese ON manga_stats (japanese_name)")
        conn.commit()
    finally:
        conn.close()

    print("Imported MAL CSV into manga_stats")


if __name__ == "__main__":
    main()
