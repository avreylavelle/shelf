import argparse
import json
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

BASE_URL = "https://api.mangadex.org/manga"


def request_json(params):
    query = urllib.parse.urlencode(params, doseq=True)
    url = f"{BASE_URL}?{query}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manga_core (
            id TEXT PRIMARY KEY,
            link TEXT,
            title_name TEXT,
            english_name TEXT,
            japanese_name TEXT,
            synonymns TEXT,
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
            content_rating TEXT,
            original_language TEXT,
            cover_url TEXT,
            links TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS manga_map (
            mangadex_id TEXT PRIMARY KEY,
            mal_id INTEGER,
            match_method TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_manga_map_mal_id ON manga_map (mal_id)")


def pick_lang_value(mapping, lang):
    if not isinstance(mapping, dict):
        return None
    if lang in mapping:
        return mapping.get(lang)
    if mapping:
        return next(iter(mapping.values()))
    return None


def flatten_titles(titles):
    items = []
    for entry in titles or []:
        if isinstance(entry, dict):
            items.extend([val for val in entry.values() if val])
    return items


def normalize_list(values):
    seen = set()
    output = []
    for val in values:
        if not val:
            continue
        if val in seen:
            continue
        seen.add(val)
        output.append(val)
    return output


def infer_type(original_language):
    mapping = {
        "ja": "Manga",
        "ko": "Manhwa",
        "zh": "Manhua",
        "zh-hk": "Manhua",
        "zh-cn": "Manhua",
    }
    if not original_language:
        return None
    return mapping.get(original_language, "Manga")


def build_cover_url(manga_id, relationships):
    for rel in relationships or []:
        if rel.get("type") != "cover_art":
            continue
        attrs = rel.get("attributes") or {}
        filename = attrs.get("fileName")
        if filename:
            return f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"
    return None


def extract_authors(relationships):
    names = []
    for rel in relationships or []:
        if rel.get("type") not in {"author", "artist"}:
            continue
        attrs = rel.get("attributes") or {}
        name = attrs.get("name")
        if name:
            names.append(name)
    return normalize_list(names)


def extract_tags(tags):
    genres = []
    themes = []
    for tag in tags or []:
        attrs = tag.get("attributes") or {}
        group = attrs.get("group")
        name = pick_lang_value(attrs.get("name") or {}, "en")
        if not name:
            continue
        if group == "genre":
            genres.append(name)
        elif group == "theme":
            themes.append(name)
    return normalize_list(genres), normalize_list(themes)


def normalize_updated_since(value):
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1]
    if "+" in text:
        text = text.split("+", 1)[0]
    if "." in text:
        text = text.split(".", 1)[0]
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def bump_timestamp(value, seconds=1):
    normalized = normalize_updated_since(value)
    if not normalized:
        return None
    dt = datetime.fromisoformat(normalized)
    dt = dt.replace(microsecond=0) + timedelta(seconds=seconds)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


def main():
    parser = argparse.ArgumentParser(description="Ingest MangaDex catalog into manga_core")
    parser.add_argument("--db", default="/opt/shelf/data/db/manga.db")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max", type=int, default=500, help="max items to fetch (0 for all)")
    parser.add_argument("--sleep", type=float, default=0.2)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--since", default="", help="updatedAtSince timestamp (ISO8601)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        ensure_tables(conn)
        total_fetched = 0
        offset = args.offset
        updated_since = normalize_updated_since(args.since) if args.since else None
        while True:
            params = {
                "limit": args.limit,
                "includes[]": ["author", "artist", "cover_art"],
                "order[updatedAt]": "asc",
            }
            if offset:
                params["offset"] = offset
            if updated_since:
                params["updatedAtSince"] = updated_since
            data = request_json(params)
            items = data.get("data") or []
            if not items:
                break

            rows = []
            map_rows = []
            for item in items:
                manga_id = item.get("id")
                attrs = item.get("attributes") or {}
                relationships = item.get("relationships") or []

                titles = attrs.get("title") or {}
                alt_titles = flatten_titles(attrs.get("altTitles"))
                english_name = pick_lang_value(titles, "en") or next((t for t in alt_titles if isinstance(t, str)), None)
                japanese_name = pick_lang_value(titles, "ja")
                title_name = english_name or japanese_name or pick_lang_value(titles, "en") or pick_lang_value(titles, "ja") or pick_lang_value(titles, "en")
                if not title_name:
                    title_name = pick_lang_value(titles, "en") or pick_lang_value(titles, "ja") or next(iter(titles.values()), None)

                genres, themes = extract_tags(attrs.get("tags"))
                authors = extract_authors(relationships)
                cover_url = build_cover_url(manga_id, relationships)
                original_language = attrs.get("originalLanguage")
                item_type = infer_type(original_language)

                links = attrs.get("links") or {}
                mal_id = links.get("mal")
                if mal_id is not None:
                    try:
                        mal_id = int(mal_id)
                    except (TypeError, ValueError):
                        mal_id = None

                rows.append(
                    (
                        manga_id,
                        f"https://mangadex.org/title/{manga_id}",
                        title_name,
                        english_name,
                        japanese_name,
                        str(normalize_list(alt_titles)),
                        item_type,
                        attrs.get("lastVolume"),
                        attrs.get("lastChapter"),
                        attrs.get("status"),
                        attrs.get("year"),
                        str(authors),
                        None,
                        str(genres),
                        str(themes),
                        attrs.get("publicationDemographic"),
                        pick_lang_value(attrs.get("description") or {}, "en"),
                        attrs.get("contentRating"),
                        original_language,
                        cover_url,
                        json.dumps(links),
                        attrs.get("updatedAt"),
                    )
                )

                if mal_id:
                    map_rows.append((manga_id, mal_id, "mal_link"))

            conn.executemany(
                """
                INSERT OR REPLACE INTO manga_core (
                    id, link, title_name, english_name, japanese_name, synonymns, item_type,
                    volumes, chapters, status, publishing_date, authors, serialization,
                    genres, themes, demographic, description, content_rating, original_language,
                    cover_url, links, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            if map_rows:
                conn.executemany(
                    """
                    INSERT OR REPLACE INTO manga_map (mangadex_id, mal_id, match_method)
                    VALUES (?, ?, ?)
                    """,
                    map_rows,
                )
            conn.commit()

            total_fetched += len(items)
            offset += args.limit
            if items:
                last_updated_raw = (items[-1].get("attributes") or {}).get("updatedAt")
                last_updated = normalize_updated_since(last_updated_raw)
                if updated_since is None:
                    updated_since = last_updated
                    offset = 0
                elif last_updated == updated_since:
                    offset += args.limit
                    if offset >= 10000:
                        updated_since = bump_timestamp(updated_since)
                        offset = 0
                else:
                    updated_since = last_updated
                    offset = 0
            if args.max and total_fetched >= args.max:
                break
            time.sleep(args.sleep)

        print(f"Fetched {total_fetched} MangaDex titles")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
