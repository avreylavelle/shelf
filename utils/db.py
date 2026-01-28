import os
import sqlite3

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(THIS_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data", "db")
DB_PATH = os.path.join(DATA_DIR, "manga.db")


def get_connection():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cur.fetchone() is not None


def ensure_users_table(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            age INTEGER,
            gender TEXT,
            preferred_genres TEXT,
            preferred_themes TEXT
        )
        """
    )
    conn.commit()


def ensure_user_ratings_table(conn):
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
