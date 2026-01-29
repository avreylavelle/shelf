CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    age INTEGER,
    gender TEXT,
    language TEXT,
    ui_prefs TEXT,
    preferred_genres TEXT,
    preferred_themes TEXT,
    blacklist_genres TEXT,
    blacklist_themes TEXT,
    signal_genres TEXT,
    signal_themes TEXT,
    password_hash TEXT
);

CREATE TABLE IF NOT EXISTS user_ratings (
    user_id TEXT NOT NULL,
    manga_id TEXT NOT NULL,
    rating REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, manga_id),
    FOREIGN KEY (user_id) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS manga_cleaned (
    id TEXT,
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
    item_type TEXT,
    volumes TEXT,
    chapters TEXT,
    status TEXT,
    publishing_date TEXT,
    authors TEXT,
    serialization TEXT,
    genres TEXT,
    themes TEXT,
    demographic TEXT
);
