import os
import sqlite3

from flask import Flask, redirect, render_template, request, session, url_for

from app.db import close_db
from app.routes.api import api_bp
from app.routes.auth import auth_bp
from app.services import recommendations as rec_service

BASE_PATH = "/shelf"
ADMIN_USER = "avreylavelle"


def _default_db_path():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(root, "Dataset", "manga.db")


def init_db(app):
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
                preferred_genres TEXT,
                preferred_themes TEXT,
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
                rating REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, manga_id)
            )
            """
        )

    cur.execute("PRAGMA table_info(users)")
    user_cols = {row[1] for row in cur.fetchall()}
    if "password_hash" not in user_cols:
        cur.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")

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

    @app.route("/")
    def root():
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
        return render_template("profile.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/ratings")
    def ratings():
        guard = _require_login()
        if guard:
            return guard
        return render_template("ratings.html", base_path=BASE_PATH)

    @app.route(f"{BASE_PATH}/recommendations")
    def recommendations():
        guard = _require_login()
        if guard:
            return guard
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

    @app.route(f"{BASE_PATH}/logout")
    def logout():
        session.pop("user_id", None)
        return redirect(url_for("login"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
