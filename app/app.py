import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for

from app.db import close_db
from app.routes.api import api_bp
from app.routes.auth import auth_bp
from app.services import recommendations as rec_service

BASE_PATH = "/shelf"  # keep all web routes under /shelf
ADMIN_USER = "avreylavelle"  # simple admin gate for now


def _default_db_path():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(root, "data", "db", "manga.db")


def init_db(app):
    # Make sure core tables exist (web shares the same DB as the CLI)
    db = sqlite3.connect(app.config["DATABASE"])
    db.row_factory = sqlite3.Row
    cur = db.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE users (
                username TEXT PRIMARY KEY,
                age INTEGER,
                gender TEXT,
                language TEXT,
                ui_prefs TEXT,
                preferred_genres TEXT,
                preferred_themes TEXT,
                blacklist_genres TEXT,
                blacklist_themes TEXT,
                password_hash TEXT
            )
            """
        )

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_ratings'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE user_ratings (
                user_id TEXT NOT NULL,
                manga_id TEXT NOT NULL,
                canonical_id TEXT,
                mdex_id TEXT,
                mal_id INTEGER,
                rating REAL,
                recommended_by_us INTEGER DEFAULT 0,
                finished_reading INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, manga_id)
            )
            """
        )


    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_dnr'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE user_dnr (
                user_id TEXT NOT NULL,
                manga_id TEXT NOT NULL,
                canonical_id TEXT,
                mdex_id TEXT,
                mal_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, manga_id)
            )
        """
        )

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_reading_list'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE user_reading_list (
                user_id TEXT NOT NULL,
                manga_id TEXT NOT NULL,
                canonical_id TEXT,
                mdex_id TEXT,
                mal_id INTEGER,
                status TEXT DEFAULT 'Plan to Read',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, manga_id)
            )
        """
        )

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_events'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE user_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                manga_id TEXT,
                event_type TEXT NOT NULL,
                event_value REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manga_stats'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE manga_stats (
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

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manga_core'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE manga_core (
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

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manga_map'")
    if not cur.fetchone():
        cur.execute(
            """
            CREATE TABLE manga_map (
                mangadex_id TEXT PRIMARY KEY,
                mal_id INTEGER,
                match_method TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_manga_map_mal_id ON manga_map (mal_id)")


    # Add status column if missing (existing DB)
    cur.execute("PRAGMA table_info(user_reading_list)")
    reading_cols = {row[1] for row in cur.fetchall()}
    if "status" not in reading_cols:
        cur.execute("ALTER TABLE user_reading_list ADD COLUMN status TEXT DEFAULT 'Plan to Read'")
    if "mdex_id" not in reading_cols:
        cur.execute("ALTER TABLE user_reading_list ADD COLUMN mdex_id TEXT")
    if "mal_id" not in reading_cols:
        cur.execute("ALTER TABLE user_reading_list ADD COLUMN mal_id INTEGER")
    if "canonical_id" not in reading_cols:
        cur.execute("ALTER TABLE user_reading_list ADD COLUMN canonical_id TEXT")

    # Add password_hash column if missing (existing DB)
    cur.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cur.fetchall()}
    if "password_hash" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")


    # Add language column if missing (existing DB)
    cur.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cur.fetchall()}
    if "language" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN language TEXT")


    # Add ui_prefs column if missing (existing DB)
    cur.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cur.fetchall()}
    if "ui_prefs" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN ui_prefs TEXT")

    # Add signal affinity columns if missing (existing DB)
    cur.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cur.fetchall()}
    if "signal_genres" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN signal_genres TEXT")
    if "signal_themes" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN signal_themes TEXT")

    # Add blacklist columns if missing (existing DB)
    cur.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cur.fetchall()}
    if "blacklist_genres" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN blacklist_genres TEXT")
    if "blacklist_themes" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN blacklist_themes TEXT")
    # Add recommended_by_us column if missing (existing DB)
    cur.execute("PRAGMA table_info(user_ratings)")
    rating_cols = {row[1] for row in cur.fetchall()}
    if "mdex_id" not in rating_cols:
        cur.execute("ALTER TABLE user_ratings ADD COLUMN mdex_id TEXT")
    if "mal_id" not in rating_cols:
        cur.execute("ALTER TABLE user_ratings ADD COLUMN mal_id INTEGER")
    if "canonical_id" not in rating_cols:
        cur.execute("ALTER TABLE user_ratings ADD COLUMN canonical_id TEXT")
    if "recommended_by_us" not in rating_cols:
        cur.execute("ALTER TABLE user_ratings ADD COLUMN recommended_by_us INTEGER DEFAULT 0")

    # Add finished_reading column if missing (existing DB)
    cur.execute("PRAGMA table_info(user_ratings)")
    rating_cols = {row[1] for row in cur.fetchall()}
    if "finished_reading" not in rating_cols:
        cur.execute("ALTER TABLE user_ratings ADD COLUMN finished_reading INTEGER DEFAULT 0")

    # Add mdex_id column if missing (existing DB)
    cur.execute("PRAGMA table_info(user_dnr)")
    dnr_cols = {row[1] for row in cur.fetchall()}
    if "mdex_id" not in dnr_cols:
        cur.execute("ALTER TABLE user_dnr ADD COLUMN mdex_id TEXT")
    if "mal_id" not in dnr_cols:
        cur.execute("ALTER TABLE user_dnr ADD COLUMN mal_id INTEGER")
    if "canonical_id" not in dnr_cols:
        cur.execute("ALTER TABLE user_dnr ADD COLUMN canonical_id TEXT")

    cur.execute("DROP VIEW IF EXISTS manga_merged")
    cur.execute(
        """
        CREATE VIEW manga_merged AS
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
        LEFT JOIN manga_stats AS stats ON stats.mal_id = map.mal_id
        """
    )
    db.commit()
    db.close()


def _is_logged_in():
    return bool(session.get("user_id"))


def _require_login():
    if not _is_logged_in():
        return redirect(url_for("login", next=request.path))
    return None


def _require_admin():
    if session.get("user_id") != ADMIN_USER:
        return redirect(url_for("dashboard"))
    return None


def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path=f"{BASE_PATH}/static",
        template_folder="templates",
    )
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dev-change-me")
    app.config["DATABASE"] = os.environ.get("MANGA_DB_PATH", _default_db_path())

    init_db(app)
    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    try:
        # Warm the options cache so the first page load doesn't pay the cost.
        rec_service.get_available_options(app.config["DATABASE"])
    except Exception:
        pass

    @app.route("/")
    def root():
        # Main landing page (Lav Labs)
        return render_template(
            "landing.html",
            base_path=BASE_PATH,
            links=[{"label": "Shelf: Manga Recommender", "href": f"{BASE_PATH}/"}],
        )

    @app.route(f"{BASE_PATH}")
    @app.route(f"{BASE_PATH}/")
    def app_landing():
        return render_template("app_landing.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/login")
    def login():
        if _is_logged_in():
            return redirect(url_for("dashboard"))
        return render_template("login.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/dashboard")
    def dashboard():
        guard = _require_login()
        if guard:
            return guard
        return render_template("dashboard.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/profile")
    def profile():
        guard = _require_login()
        if guard:
            return guard
        genres, themes = rec_service.get_available_options(app.config["DATABASE"])
        return render_template("profile.html", base_path=BASE_PATH, genres=genres, themes=themes)

    @app.route(f"{BASE_PATH}/ratings")
    def ratings():
        guard = _require_login()
        if guard:
            return guard
        return render_template("ratings.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/search")
    def search():
        guard = _require_login()
        if guard:
            return guard
        genres, themes = rec_service.get_available_options(app.config["DATABASE"])
        return render_template("search.html", base_path=BASE_PATH, genres=genres, themes=themes)

    @app.route(f"{BASE_PATH}/recommendations")
    def recommendations():
        guard = _require_login()
        if guard:
            return guard
        # Pull options once (cached in the service)
        genres, themes = rec_service.get_available_options(app.config["DATABASE"])
        return render_template(
            "recommendations.html",
            base_path=BASE_PATH,
            genres=genres,
            themes=themes,
        )

    @app.route(f"{BASE_PATH}/admin")
    def admin():
        guard = _require_login()
        if guard:
            return guard
        admin_guard = _require_admin()
        if admin_guard:
            return admin_guard
        return render_template("admin.html", base_path=BASE_PATH)

    

    @app.route(f"{BASE_PATH}/do-not-recommend")
    def do_not_recommend():
        guard = _require_login()
        if guard:
            return guard
        return render_template("dnr.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/reading-list")
    def reading_list():
        guard = _require_login()
        if guard:
            return guard
        return render_template("reading_list.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/logout")
    def logout():
        session.pop("user_id", None)
        return redirect(url_for("login"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
