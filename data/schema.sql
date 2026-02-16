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
    password_hash TEXT,
    is_admin INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_ratings (
    user_id TEXT NOT NULL,
    manga_id TEXT NOT NULL,
    canonical_id TEXT,
    mdex_id TEXT,
    mal_id INTEGER,
    rating REAL,
    recommended_by_us INTEGER DEFAULT 0,
    finished_reading INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, manga_id),
    FOREIGN KEY (user_id) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS user_dnr (
    user_id TEXT NOT NULL,
    manga_id TEXT NOT NULL,
    canonical_id TEXT,
    mdex_id TEXT,
    mal_id INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, manga_id),
    FOREIGN KEY (user_id) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS user_reading_list (
    user_id TEXT NOT NULL,
    manga_id TEXT NOT NULL,
    canonical_id TEXT,
    mdex_id TEXT,
    mal_id INTEGER,
    status TEXT DEFAULT 'Plan to Read',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, manga_id),
    FOREIGN KEY (user_id) REFERENCES users(username)
);

CREATE TABLE IF NOT EXISTS user_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    manga_id TEXT,
    event_type TEXT NOT NULL,
    event_value REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    genres TEXT,
    themes TEXT,
    blacklist_genres TEXT,
    blacklist_themes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_request_cache (
    user_id TEXT PRIMARY KEY,
    request_count INTEGER DEFAULT 0,
    preferred_genres TEXT,
    preferred_themes TEXT,
    blacklist_genres TEXT,
    blacklist_themes TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(username)
);

CREATE INDEX IF NOT EXISTS idx_user_requests_user_time ON user_requests (user_id, created_at);

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
);

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
);

CREATE TABLE IF NOT EXISTS manga_map (
    mangadex_id TEXT PRIMARY KEY,
    mal_id INTEGER,
    match_method TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_manga_stats_title ON manga_stats (title_name);
CREATE INDEX IF NOT EXISTS idx_manga_stats_english ON manga_stats (english_name);
CREATE INDEX IF NOT EXISTS idx_manga_stats_japanese ON manga_stats (japanese_name);
CREATE INDEX IF NOT EXISTS idx_manga_map_mal_id ON manga_map (mal_id);

CREATE VIEW IF NOT EXISTS manga_merged AS
SELECT
    core.id AS mangadex_id,
    core.link,
    core.title_name,
    core.english_name,
    core.japanese_name,
    core.synonymns,
    core.item_type,
    core.volumes,
    core.chapters,
    core.status,
    core.publishing_date,
    core.authors,
    core.serialization,
    core.genres,
    core.themes,
    core.demographic,
    core.description,
    core.content_rating,
    core.original_language,
    core.cover_url,
    core.links,
    core.updated_at,
    stats.mal_id,
    stats.score,
    stats.scored_by,
    stats.ranked,
    stats.popularity,
    stats.members,
    stats.favorited
FROM manga_core AS core
LEFT JOIN manga_map AS map ON map.mangadex_id = core.id
LEFT JOIN manga_stats AS stats ON stats.mal_id = map.mal_id;
