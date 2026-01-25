import sqlite3
import string
from difflib import get_close_matches
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from data.repository import Repository
from utils.db import DB_PATH, ensure_users_table, get_connection, table_exists
from utils.parsing import parse_dict


class SqliteRepository(Repository):
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._manga_cache = None

    def _ensure_user_ratings_table(self, conn):
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_ratings (
                user_id TEXT NOT NULL,
                manga_id TEXT NOT NULL,
                rating REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, manga_id),
                FOREIGN KEY (user_id) REFERENCES users(username)
            )
            """
        )
        conn.commit()

    def get_all_users(self) -> pd.DataFrame:
        with get_connection() as conn:
            ensure_users_table(conn)
            return pd.read_sql_query("SELECT * FROM users", conn)

    def _row_to_profile(self, row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "username": row["username"],
            "age": None if pd.isna(row["age"]) else int(row["age"]),
            "gender": row["gender"] if isinstance(row["gender"], str) else "",
            "preferred_genres": parse_dict(row["preferred_genres"]),
            "preferred_themes": parse_dict(row["preferred_themes"]),
            "read_manga": parse_dict(row["read_manga"]),
        }

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            ensure_users_table(conn)
            cur = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_profile(row)

    def create_user(
        self,
        username: str,
        age: Optional[int] = None,
        gender: str = "",
        preferred_genres: Optional[Dict[str, Any]] = None,
        preferred_themes: Optional[Dict[str, Any]] = None,
        read_manga: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        profile = {
            "username": username,
            "age": age,
            "gender": gender or "",
            "preferred_genres": preferred_genres or {},
            "preferred_themes": preferred_themes or {},
            "read_manga": read_manga or {},
        }
        self._save_profile(profile)
        return profile

    def _save_profile(self, profile: Dict[str, Any]) -> None:
        with get_connection() as conn:
            ensure_users_table(conn)
            self._ensure_user_ratings_table(conn)
            conn.execute("DELETE FROM users WHERE username = ?", (profile["username"],))
            conn.execute(
                """
                INSERT INTO users (username, age, gender, preferred_genres, preferred_themes, read_manga)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    profile["username"],
                    profile.get("age", None),
                    profile.get("gender", ""),
                    str(profile.get("preferred_genres", {})),
                    str(profile.get("preferred_themes", {})),
                    str(profile.get("read_manga", {})),
                ),
            )
            conn.commit()

            # Mirror read_manga dict into user_ratings for normalized access
            read_manga = profile.get("read_manga", {})
            conn.execute(
                "DELETE FROM user_ratings WHERE user_id = ?",
                (profile["username"],),
            )
            for manga_id, rating in read_manga.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO user_ratings (user_id, manga_id, rating)
                    VALUES (?, ?, ?)
                    """,
                    (profile["username"], manga_id, rating),
                )
            conn.commit()

    def get_manga_by_id(self, manga_id: str) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            if not table_exists(conn, "manga_cleaned"):
                return None
            cur = conn.execute(
                "SELECT * FROM manga_cleaned WHERE id = ?",
                (manga_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return dict(row)

    def get_manga_dataset(self) -> pd.DataFrame:
        if self._manga_cache is not None:
            return self._manga_cache
        with get_connection() as conn:
            if not table_exists(conn, "manga_cleaned"):
                raise FileNotFoundError(
                    "Missing SQLite table 'manga_cleaned'. Import data into manga.db first."
                )
            self._manga_cache = pd.read_sql_query("SELECT * FROM manga_cleaned", conn)
            return self._manga_cache

    def search_manga_titles(
        self, query: str, limit: int = 20, lang: str = "en"
    ) -> Dict[str, Any]:
        df = self.get_manga_dataset()
        all_titles = df["title_name"].astype(str).tolist()
        title_lookup = {t.lower(): t for t in all_titles}
        requested_lower = query.lower()

        exact = title_lookup.get(requested_lower)

        # Substring matches, sorted by internal score (desc)
        substring_match = []
        if requested_lower not in title_lookup:
            for title_name in title_lookup.keys():
                translator = str.maketrans({p: " " for p in string.punctuation})
                translated_title_name = title_name.translate(translator)
                if requested_lower in translated_title_name.lower():
                    substring_match.append(title_name)

        temp = []
        for name in substring_match:
            real_title = title_lookup[name]
            try:
                score = float(
                    df.loc[df["title_name"] == real_title, "score"].fillna(0).iloc[0]
                )
            except Exception:
                score = 0.0
            temp.append((score, name))

        temp.sort(reverse=True)
        substring_match = [name for score, name in temp][:limit]

        # Fuzzy matches, sorted by internal score (desc)
        fuzzy = []
        if not exact:
            temp = []
            suggestions = get_close_matches(
                requested_lower, list(title_lookup.keys()), n=limit, cutoff=0.1
            )
            for name in suggestions:
                real_title = title_lookup[name]
                try:
                    score = float(
                        df.loc[df["title_name"] == real_title, "score"].fillna(0).iloc[0]
                    )
                except Exception:
                    score = 0.0
                temp.append((score, name))

            temp.sort(reverse=True)
            fuzzy = [name for score, name in temp][:limit]

        return {
            "exact": exact,
            "substring": substring_match,
            "fuzzy": fuzzy,
            "title_lookup": title_lookup,
        }

    def get_user_ratings(self, user_id: str) -> List[Tuple[str, Any]]:
        with get_connection() as conn:
            ensure_users_table(conn)
            self._ensure_user_ratings_table(conn)
            cur = conn.execute(
                "SELECT manga_id, rating FROM user_ratings WHERE user_id = ?",
                (user_id,),
            )
            rows = cur.fetchall()
            if rows:
                return [(row[0], row[1]) for row in rows]

            # Backfill from users.read_manga if present
            cur = conn.execute(
                "SELECT read_manga FROM users WHERE username = ?",
                (user_id,),
            )
            row = cur.fetchone()
            if row is None:
                return []
            read_manga = parse_dict(row[0])
            if not read_manga:
                return []
            conn.execute(
                "DELETE FROM user_ratings WHERE user_id = ?",
                (user_id,),
            )
            for manga_id, rating in read_manga.items():
                conn.execute(
                    """
                    INSERT OR REPLACE INTO user_ratings (user_id, manga_id, rating)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, manga_id, rating),
                )
            conn.commit()
            return list(read_manga.items())

    def upsert_rating(
        self, user_id: str, manga_id: str, rating: Any
    ) -> Optional[Dict[str, Any]]:
        profile = self.get_user_by_username(user_id)
        if profile is None:
            return None
        with get_connection() as conn:
            ensure_users_table(conn)
            self._ensure_user_ratings_table(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO user_ratings (user_id, manga_id, rating)
                VALUES (?, ?, ?)
                """,
                (user_id, manga_id, rating),
            )
            conn.commit()
        profile["read_manga"][manga_id] = rating
        self._save_profile(profile)
        return profile

    def delete_rating(self, user_id: str, manga_id: str) -> Optional[Dict[str, Any]]:
        profile = self.get_user_by_username(user_id)
        if profile is None:
            return None
        with get_connection() as conn:
            ensure_users_table(conn)
            self._ensure_user_ratings_table(conn)
            conn.execute(
                "DELETE FROM user_ratings WHERE user_id = ? AND manga_id = ?",
                (user_id, manga_id),
            )
            conn.commit()
        profile["read_manga"].pop(manga_id, None)
        self._save_profile(profile)
        return profile
