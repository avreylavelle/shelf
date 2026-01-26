from functools import wraps

import csv
import io

from flask import Blueprint, jsonify, request, session, current_app, Response

from app.services import ratings as ratings_service
from app.services import recommendations as rec_service
from app.services import profile as profile_service
from app.repos import manga as manga_repo

api_bp = Blueprint("api", __name__, url_prefix="/shelf/api")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "auth required"}), 401
        return fn(*args, **kwargs)

    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({"error": "auth required"}), 401
        if session.get("user_id") != "avreylavelle":
            return jsonify({"error": "admin only"}), 403
        return fn(*args, **kwargs)

    return wrapper




def _get_value(row, key):
    try:
        return row.get(key)
    except AttributeError:
        return row[key] if hasattr(row, "keys") and key in row.keys() else None


def _display_title(row, language):
    if language == "Japanese":
        return _get_value(row, "japanese_name") or _get_value(row, "title_name") or _get_value(row, "manga_id")
    return _get_value(row, "english_name") or _get_value(row, "title_name") or _get_value(row, "manga_id")

def _parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


@api_bp.get("/session")
def get_session():
    user_id = session.get("user_id")
    return jsonify({"logged_in": bool(user_id), "user": user_id})


@api_bp.get("/profile")
@login_required
def get_profile():
    user_id = session["user_id"]
    profile = profile_service.get_profile(user_id)
    return jsonify({"profile": profile})


@api_bp.put("/profile")
@login_required
def update_profile():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    age = data.get("age")
    gender = data.get("gender")
    language = data.get("language")
    new_username = (data.get("username") or "").strip()

    if age == "":
        age = None
    if age is not None:
        try:
            age = int(age)
        except (TypeError, ValueError):
            return jsonify({"error": "age must be a number"}), 400


    allowed_languages = {"English", "Japanese"}
    if language and language not in allowed_languages:
        return jsonify({"error": "language must be English or Japanese"}), 400
    if language is None:
        existing = profile_service.get_profile(user_id)
        language = (existing or {}).get("language") or "English"
    if new_username:
        error = profile_service.change_username(user_id, new_username)
        if error:
            return jsonify({"error": error}), 400
        session["user_id"] = new_username
        user_id = new_username

    profile_service.update_profile(user_id, age=age, gender=gender, language=language)
    profile = profile_service.get_profile(user_id)
    return jsonify({"ok": True, "profile": profile})


@api_bp.post("/profile/clear-history")
@login_required
def clear_history():
    user_id = session["user_id"]
    profile_service.clear_history(user_id)
    return jsonify({"ok": True})


@api_bp.get("/ratings")
@login_required
def list_ratings():
    user_id = session["user_id"]
    sort = (request.args.get("sort") or "chron").strip()
    allowed = {"chron", "alpha", "rating_desc", "rating_asc"}
    if sort not in allowed:
        sort = "chron"

    rows = ratings_service.list_ratings(user_id, sort=sort)
    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"
    payload = [
        {
            "user_id": row["user_id"],
            "manga_id": row["manga_id"],
            "display_title": _display_title(row, language),
            "english_name": row["english_name"],
            "japanese_name": row["japanese_name"],
            "rating": row["rating"],
            "recommended_by_us": row["recommended_by_us"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return jsonify({"items": payload})


@api_bp.get("/ratings/map")
@login_required
def ratings_map():
    # Used to prefill rating boxes on recommendations
    user_id = session["user_id"]
    items = ratings_service.list_ratings_map(user_id)
    return jsonify({"items": items})


@api_bp.post("/ratings")
@login_required
def upsert_rating():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    manga_id = (data.get("manga_id") or "").strip()
    rating = data.get("rating")
    recommended_by_us = data.get("recommended_by_us")

    error = ratings_service.set_rating(user_id, manga_id, rating, recommended_by_us)
    if error:
        return jsonify({"error": error}), 400

    return jsonify({"ok": True})


@api_bp.delete("/ratings/<path:manga_id>")
@login_required
def delete_rating(manga_id):
    user_id = session["user_id"]
    manga_id = (manga_id or "").strip()
    error = ratings_service.delete_rating(user_id, manga_id)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"ok": True})


@api_bp.get("/manga/search")
@login_required
def search_manga():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify({"items": []})

    rows = manga_repo.search_by_title(query, limit=10)
    profile = profile_service.get_profile(session["user_id"])
    language = (profile or {}).get("language") or "English"
    payload = [
        {
            "id": row["id"],
            "title": row["title_name"],
            "display_title": _display_title(row, language),
            "english_name": row["english_name"],
            "japanese_name": row["japanese_name"],
            "score": row["score"],
            "genres": row["genres"],
            "themes": row["themes"],
        }
        for row in rows
    ]
    return jsonify({"items": payload})


@api_bp.get("/manga/details")
@login_required
def manga_details():
    title = (request.args.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title required"}), 400
    row = manga_repo.get_by_title(title)
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"item": dict(row)})


# Admin endpoints (restricted to avreylavelle)
@api_bp.post("/admin/switch-user")
@admin_required
def admin_switch_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"error": "username required"}), 400
    user = profile_service.get_profile(username)
    if not user:
        return jsonify({"error": "user not found"}), 404
    session["user_id"] = username
    return jsonify({"ok": True, "user": username})


@api_bp.get("/admin/ratings/export")
@admin_required
def admin_export_ratings():
    user_id = session["user_id"]
    rows = ratings_service.list_ratings(user_id, sort="chron")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["manga_id", "rating"])  # header line
    for row in rows:
        writer.writerow([row["manga_id"], row["rating"]])
    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=ratings.csv"},
    )


@api_bp.post("/admin/ratings/import")
@admin_required
def admin_import_ratings():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    csv_text = data.get("csv") or ""
    if not csv_text.strip():
        return jsonify({"error": "csv required"}), 400

    reader = csv.DictReader(io.StringIO(csv_text))
    count = 0
    for row in reader:
        manga_id = (row.get("manga_id") or "").strip()
        rating = row.get("rating")
        if not manga_id:
            continue
        error = ratings_service.set_rating(user_id, manga_id, rating)
        if error:
            return jsonify({"error": error}), 400
        count += 1

    return jsonify({"ok": True, "count": count})


@api_bp.get("/recommendations/options")
def recommendation_options():
    genres, themes = rec_service.get_available_options(current_app.config["DATABASE"])
    return jsonify({"genres": genres, "themes": themes})


@api_bp.get("/recommendations")
@login_required
def recommendations():
    user_id = session["user_id"]
    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"

    results, used_current = rec_service.recommend_for_user(
        current_app.config["DATABASE"],
        user_id,
        [],
        [],
        limit=20,
        update_profile=False,
    )
    items = []
    for item in results or []:
        item["display_title"] = _display_title(item, language)
        items.append(item)
    return jsonify({"items": items, "used_current": used_current})


@api_bp.post("/recommendations")
@login_required
def recommendations_with_prefs():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    current_genres = _parse_list(data.get("genres"))
    current_themes = _parse_list(data.get("themes"))

    # Keep history in sync (this is your "memory")
    profile_service.increment_preferences(user_id, current_genres, current_themes)

    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"

    results, used_current = rec_service.recommend_for_user(
        current_app.config["DATABASE"],
        user_id,
        current_genres,
        current_themes,
        limit=20,
        update_profile=True,
    )
    items = []
    for item in results or []:
        item["display_title"] = _display_title(item, language)
        items.append(item)
    return jsonify({"items": items, "used_current": used_current})
