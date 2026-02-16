"""Script to build MangaDex-to-MAL mappings using title heuristics."""

import argparse
import ast
import re
import sqlite3


def normalize_title(value):
    """Normalize title for consistent comparisons."""
    if not value:
        return ""
    value = str(value).lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_item_type(value):
    """Normalize item type for consistent comparisons."""
    if not value:
        return None
    text = str(value).strip().lower()
    mapping = {
        "manga": "manga",
        "manhwa": "manhwa",
        "manhua": "manhua",
    }
    return mapping.get(text)


def parse_list(value):
    """Parse list into normalized data."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    text = str(value)
    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass
    return [item.strip() for item in text.split(",") if item.strip()]


def extract_year(value):
    """Handle extract year for this module."""
    if not value:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None


def main():
    """Run the script entrypoint."""
    parser = argparse.ArgumentParser(description="Build MangaDex -> MAL map using title fallback")
    parser.add_argument("--db", default="/opt/shelf/data/db/manga.db")
    parser.add_argument("--max", type=int, default=0, help="max mappings to add (0 = all)")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT mal_id FROM manga_map")
        existing_mal = {row[0] for row in cur.fetchall() if row[0] is not None}

        cur = conn.execute(
            "SELECT mal_id, title_name, english_name, japanese_name, synonymns, publishing_date, item_type FROM manga_stats"
        )
        title_index = {}
        mal_year = {}
        for row in cur.fetchall():
            mal_id = row["mal_id"]
            if mal_id is None:
                continue
            mal_year[mal_id] = extract_year(row["publishing_date"])
            mal_type = normalize_item_type(row["item_type"])
            titles = [row["title_name"], row["english_name"], row["japanese_name"]]
            titles += parse_list(row["synonymns"])
            for title in titles:
                norm = normalize_title(title)
                if not norm:
                    continue
                bucket = title_index.setdefault(norm, {"_all": set()})
                bucket["_all"].add(mal_id)
                if mal_type:
                    bucket.setdefault(mal_type, set()).add(mal_id)

        cur = conn.execute(
            "SELECT id, title_name, english_name, japanese_name, synonymns, publishing_date, item_type FROM manga_core"
        )
        to_insert = []
        added = 0
        for row in cur.fetchall():
            mangadex_id = row["id"]
            exists = conn.execute(
                "SELECT 1 FROM manga_map WHERE mangadex_id = ?",
                (mangadex_id,),
            ).fetchone()
            if exists:
                continue
            mdex_type = normalize_item_type(row["item_type"])
            titles = [row["title_name"], row["english_name"], row["japanese_name"]]
            titles += parse_list(row["synonymns"])
            candidates = set()
            for title in titles:
                norm = normalize_title(title)
                if not norm:
                    continue
                bucket = title_index.get(norm)
                if not bucket:
                    continue
                if mdex_type:
                    candidates.update(bucket.get(mdex_type, set()))
                else:
                    candidates.update(bucket.get("_all", set()))
            if not candidates and mdex_type:
                for title in titles:
                    norm = normalize_title(title)
                    if not norm:
                        continue
                    bucket = title_index.get(norm)
                    if not bucket:
                        continue
                    candidates.update(bucket.get("_all", set()))
            if not candidates:
                continue

            chosen = None
            method = None
            if len(candidates) == 1:
                chosen = next(iter(candidates))
                method = "title_exact"
            else:
                year = extract_year(row["publishing_date"])
                if year is not None:
                    filtered = {c for c in candidates if mal_year.get(c) == year}
                    if len(filtered) == 1:
                        chosen = next(iter(filtered))
                        method = "title_year"
            if chosen is None:
                continue
            if chosen in existing_mal:
                continue

            to_insert.append((mangadex_id, chosen, method))
            existing_mal.add(chosen)
            added += 1
            if args.max and added >= args.max:
                break

        if to_insert:
            conn.executemany(
                "INSERT OR REPLACE INTO manga_map (mangadex_id, mal_id, match_method) VALUES (?, ?, ?)",
                to_insert,
            )
            conn.commit()
        print(f"Added {added} fallback mappings")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
