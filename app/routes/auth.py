"""Authentication API routes for register, login, and account actions."""

from flask import Blueprint, jsonify, request, session

from app.services import auth as auth_service


auth_bp = Blueprint("auth", __name__, url_prefix="/shelf/api/auth")


def _json_error(message, status=400):
    """Handle json error for this module."""
    return jsonify({"error": message}), status


@auth_bp.post("/register")
def register():
    """Handle register for this module."""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return _json_error("username and password required")

    user, error = auth_service.register(username, password)
    if error:
        return _json_error(error)

    return jsonify({"ok": True, "user": user})


@auth_bp.post("/login")
def login():
    """Handle login for this module."""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return _json_error("username and password required")

    user, error = auth_service.login(username, password)
    if error:
        return _json_error(error, status=401)

    session["user_id"] = user["username"]
    return jsonify({"ok": True, "user": user})


@auth_bp.post("/logout")
def logout():
    """Handle logout for this module."""
    session.pop("user_id", None)
    return jsonify({"ok": True})


@auth_bp.post("/delete-account")
def delete_account():
    """Delete account."""
    user_id = session.get("user_id")
    if not user_id:
        return _json_error("auth required", status=401)

    error = auth_service.delete_account(user_id)
    if error:
        return _json_error(error, status=400)

    session.pop("user_id", None)
    return jsonify({"ok": True})


@auth_bp.post("/change-password")
def change_password():
    """Change password after validation."""
    user_id = session.get("user_id")
    if not user_id:
        return _json_error("auth required", status=401)

    data = request.get_json(silent=True) or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    if not current_password or not new_password:
        return _json_error("current_password and new_password required")

    error = auth_service.change_password(user_id, current_password, new_password)
    if error:
        return _json_error(error, status=400)

    return jsonify({"ok": True})
