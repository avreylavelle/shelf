from functools import wraps

import csv
import io

from flask import Blueprint, jsonify, request, session, current_app, Response

from app.services import ratings as ratings_service
from app.services import recommendations as rec_service
from utils.parsing import parse_list
from app.services import profile as profile_service
from app.services import dnr as dnr_service
from app.services import reading_list as reading_list_service
from app.services import signals as signals_service
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



def _sanitize_item(item):
    # Avoid invalid JSON (NaN) and ensure a title string is present
    for key in ("score", "internal_score", "match_score", "combined_score"):
        value = item.get(key)
        try:
            if value != value:  # NaN check
                item[key] = None
        except Exception:
            pass
    return item

def _parse_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [v.strip() for v in str(value).split(",") if v.strip()]


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@api_bp.get("/session")
def get_session():
    user_id = session.get("user_id")
    return jsonify({"logged_in": bool(user_id), "user": user_id})




@api_bp.get("/ui-prefs")
@login_required
def get_ui_prefs():
    user_id = session["user_id"]
    prefs = profile_service.get_ui_prefs(user_id)
    return jsonify({"prefs": prefs})


@api_bp.put("/ui-prefs")
@login_required
def set_ui_prefs():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    current = profile_service.get_ui_prefs(user_id)
    merged = {**current, **data}
    profile_service.set_ui_prefs(user_id, merged)
    return jsonify({"ok": True, "prefs": merged})

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
    new_username_norm = new_username.lower() if new_username else ""

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
        error = profile_service.change_username(user_id, new_username_norm)
        if error:
            return jsonify({"error": error}), 400
        session["user_id"] = new_username_norm
        user_id = new_username_norm

    profile_service.update_profile(user_id, age=age, gender=gender, language=language)
    profile = profile_service.get_profile(user_id)
    return jsonify({"ok": True, "profile": profile})


@api_bp.post("/profile/clear-history")
@login_required
def clear_history():
    user_id = session["user_id"]
    profile_service.clear_history(user_id)
    return jsonify({"ok": True})




@api_bp.get("/dnr")
@login_required
def list_dnr():
    user_id = session["user_id"]
    sort = (request.args.get("sort") or "chron").strip()
    allowed = {"chron", "alpha"}
    if sort not in allowed:
        sort = "chron"
    rows = dnr_service.list_items(user_id, sort=sort)
    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"
    payload = [
        {
            "user_id": row["user_id"],
            "manga_id": row["manga_id"],
            "status": row["status"] if "status" in row.keys() else None,
            "display_title": _display_title(row, language),
            "english_name": row["english_name"],
            "japanese_name": row["japanese_name"],
            "item_type": _get_value(row, "item_type"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    if sort == "alpha":
        payload.sort(key=lambda item: (item.get("display_title") or "").lower())
    return jsonify({"items": payload})


@api_bp.post("/dnr")
@login_required
def add_dnr():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    manga_id = (data.get("manga_id") or "").strip()
    error = dnr_service.add_item(user_id, manga_id)
    if error:
        return jsonify({"error": error}), 400
    signals_service.record_event(user_id, "dnr", manga_id)
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@api_bp.delete("/dnr/<path:manga_id>")
@login_required
def remove_dnr(manga_id):
    user_id = session["user_id"]
    manga_id = (manga_id or "").strip()
    error = dnr_service.remove_item(user_id, manga_id)
    if error:
        return jsonify({"error": error}), 400
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
    return jsonify({"ok": True})

@api_bp.get("/reading-list")
@login_required
def list_reading_list():
    user_id = session["user_id"]
    sort = (request.args.get("sort") or "chron").strip()
    allowed = {"chron", "alpha"}
    if sort not in allowed:
        sort = "chron"
    rows = reading_list_service.list_items(user_id, sort=sort)
    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"
    payload = [
        {
            "user_id": row["user_id"],
            "manga_id": row["manga_id"],
            "status": row["status"] if "status" in row.keys() else None,
            "display_title": _display_title(row, language),
            "english_name": row["english_name"],
            "japanese_name": row["japanese_name"],
            "item_type": _get_value(row, "item_type"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    if sort == "alpha":
        payload.sort(key=lambda item: (item.get("display_title") or "").lower())
    return jsonify({"items": payload})


@api_bp.post("/reading-list")
@login_required
def add_reading_list():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    manga_id = (data.get("manga_id") or "").strip()
    status = (data.get("status") or "Plan to Read").strip()
    error = reading_list_service.add_item(user_id, manga_id, status=status)
    if error:
        return jsonify({"error": error}), 400
    signals_service.record_event(user_id, "reading_list", manga_id)
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@api_bp.put("/reading-list")
@login_required
def update_reading_list_status():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    manga_id = (data.get("manga_id") or "").strip()
    status = (data.get("status") or "").strip()
    error = reading_list_service.update_status(user_id, manga_id, status)
    if error:
        return jsonify({"error": error}), 400
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@api_bp.delete("/reading-list/<path:manga_id>")
@login_required
def remove_reading_list(manga_id):
    user_id = session["user_id"]
    manga_id = (manga_id or "").strip()
    error = reading_list_service.remove_item(user_id, manga_id)
    if error:
        return jsonify({"error": error}), 400
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
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
            "status": row["status"] if "status" in row.keys() else None,
            "display_title": _display_title(row, language),
            "english_name": row["english_name"],
            "japanese_name": row["japanese_name"],
            "item_type": _get_value(row, "item_type"),
            "rating": row["rating"],
            "recommended_by_us": row["recommended_by_us"],
            "finished_reading": row["finished_reading"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    if sort == "alpha":
        payload.sort(key=lambda item: (item.get("display_title") or "").lower())
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
    finished_reading = data.get("finished_reading")

    error = ratings_service.set_rating(user_id, manga_id, rating, recommended_by_us, finished_reading)
    if error:
        return jsonify({"error": error}), 400

    if rating is not None:
        signals_service.record_event(user_id, "rated", manga_id, rating)
    if finished_reading:
        signals_service.record_event(user_id, "finished", manga_id)
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
    return jsonify({"ok": True})


@api_bp.delete("/ratings/<path:manga_id>")
@login_required
def delete_rating(manga_id):
    user_id = session["user_id"]
    manga_id = (manga_id or "").strip()
    error = ratings_service.delete_rating(user_id, manga_id)
    if error:
        return jsonify({"error": error}), 400
    signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
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
            "item_type": row["item_type"],
            "score": row["score"],
            "genres": row["genres"],
            "themes": row["themes"],
        }
        for row in rows
    ]
    return jsonify({"items": payload})


@api_bp.get("/manga/browse")
@login_required
def browse_manga():
    sort = (request.args.get("sort") or "popularity").strip().lower()
    genres = _parse_list(request.args.get("genres") or request.args.get("genre"))
    themes = _parse_list(request.args.get("themes") or request.args.get("theme"))
    content_types = _parse_list(request.args.get("content_types") or request.args.get("types"))
    status = (request.args.get("status") or "").strip()
    min_score = request.args.get("min_score")
    limit = request.args.get("limit") or 50

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 50
    limit = max(1, min(limit, 200))

    min_score_val = None
    if min_score not in (None, ""):
        try:
            min_score_val = float(min_score)
        except (TypeError, ValueError):
            min_score_val = None

    db_path = rec_service._resolve_db_path(current_app.config["DATABASE"])
    df = rec_service._load_manga_df(db_path).copy()

    df["genres"] = df["genres"].apply(parse_list)
    df["themes"] = df["themes"].apply(parse_list)

    if genres:
        df = df[df["genres"].apply(lambda values: any(g in values for g in genres))]
    if themes:
        df = df[df["themes"].apply(lambda values: any(t in values for t in themes))]

    if content_types:
        allowed = {str(t).strip() for t in content_types if str(t).strip()}
        if allowed:
            df = df[df["item_type"].isin(allowed)]

    if min_score_val is not None:
        df = df[df["score"].fillna(0) >= min_score_val]

    if status:
        df = df[df["status"].fillna("").str.lower() == status.lower()]

    sort_map = {
        "popularity": ("popularity", True),
        "score": ("score", False),
        "members": ("members", False),
        "favorited": ("favorited", False),
    }
    sort_key, ascending = sort_map.get(sort, ("popularity", True))
    if sort_key in df.columns:
        df = df.sort_values(by=sort_key, ascending=ascending, na_position="last")

    profile = profile_service.get_profile(session["user_id"])
    language = (profile or {}).get("language") or "English"

    payload = []
    for _, row in df.head(limit).iterrows():
        item = {
            "id": row.get("id"),
            "title": row.get("title_name"),
            "display_title": _display_title(row, language),
            "english_name": row.get("english_name"),
            "japanese_name": row.get("japanese_name"),
            "item_type": row.get("item_type"),
            "score": row.get("score"),
            "popularity": row.get("popularity"),
            "members": row.get("members"),
            "favorited": row.get("favorited"),
            "genres": row.get("genres"),
            "themes": row.get("themes"),
        }
        payload.append(_sanitize_item(item))

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


@api_bp.post("/events")
@login_required
def record_event():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    event_type = (data.get("event_type") or "").strip().lower()
    manga_id = (data.get("manga_id") or "").strip()
    value = data.get("value")

    allowed = {"clicked", "details", "reroll"}
    if event_type not in allowed:
        return jsonify({"error": "invalid event_type"}), 400

    signals_service.record_event(user_id, event_type, manga_id or None, value)
    if event_type in {"clicked", "details"}:
        signals_service.recompute_affinities(user_id, current_app.config["DATABASE"])
    return jsonify({"ok": True})


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


@api_bp.get("/admin/model-snapshot")
@admin_required
def admin_model_snapshot():
    username = (request.args.get("user") or "").strip()
    if not username:
        username = session["user_id"]
    snapshot = signals_service.get_snapshot(username)
    return jsonify({"snapshot": snapshot})


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


@api_bp.get("/recommendations")
@login_required
def recommendations():
    user_id = session["user_id"]
    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"

    mode = (request.args.get("mode") or "").strip() or None
    reroll = _parse_bool(request.args.get("reroll"))
    diversify = _parse_bool(request.args.get("diversify"), True)
    novelty = _parse_bool(request.args.get("novelty"), False)
    personalize = _parse_bool(request.args.get("personalize"), True)
    min_year = request.args.get("min_year")
    try:
        min_year = int(min_year) if min_year is not None else None
    except (TypeError, ValueError):
        min_year = None
    content_types = _parse_list(request.args.get("content_types"))
    blacklist_genres = _parse_list(request.args.get("blacklist_genres"))
    blacklist_themes = _parse_list(request.args.get("blacklist_themes"))
    results, used_current = rec_service.recommend_for_user(
        current_app.config["DATABASE"],
        user_id,
        [],
        [],
        limit=20,
        mode=mode,
        reroll=reroll,
        diversify=diversify,
        novelty=novelty,
        personalize=personalize,
        earliest_year=min_year,
        content_types=content_types,
        blacklist_genres=blacklist_genres,
        blacklist_themes=blacklist_themes,
    )
    items = []
    for item in results or []:
        item["display_title"] = _display_title(item, language)
        items.append(_sanitize_item(item))
    return jsonify({"items": items, "used_current": used_current, "mode": mode or "v3"})


@api_bp.post("/recommendations")
@login_required
def recommendations_with_prefs():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    current_genres = _parse_list(data.get("genres"))
    current_themes = _parse_list(data.get("themes"))
    blacklist_genres = _parse_list(data.get("blacklist_genres"))
    blacklist_themes = _parse_list(data.get("blacklist_themes"))
    mode = (data.get("mode") or "").strip() or None
    reroll = _parse_bool(data.get("reroll"))
    diversify = _parse_bool(data.get("diversify"), True)
    novelty = _parse_bool(data.get("novelty"), False)
    personalize = _parse_bool(data.get("personalize"), True)
    min_year = data.get("min_year")
    try:
        min_year = int(min_year) if min_year is not None else None
    except (TypeError, ValueError):
        min_year = None
    content_types = _parse_list(data.get("content_types"))

    # Keep history in sync (this is your "memory")
    if not reroll:
        profile_service.increment_preferences(user_id, current_genres, current_themes)
        profile_service.increment_blacklist_history(user_id, blacklist_genres, blacklist_themes)

    profile = profile_service.get_profile(user_id)
    language = (profile or {}).get("language") or "English"

    results, used_current = rec_service.recommend_for_user(
        current_app.config["DATABASE"],
        user_id,
        current_genres,
        current_themes,
        limit=20,
        mode=mode,
        reroll=reroll,
        diversify=diversify,
        novelty=novelty,
        personalize=personalize,
        earliest_year=min_year,
        content_types=content_types,
        blacklist_genres=blacklist_genres,
        blacklist_themes=blacklist_themes,
    )
    items = []
    for item in results or []:
        item["display_title"] = _display_title(item, language)
        items.append(_sanitize_item(item))
    return jsonify({"items": items, "used_current": used_current, "mode": mode or "v3"})
