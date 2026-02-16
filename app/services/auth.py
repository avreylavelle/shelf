"""Authentication business logic and password validation flow."""

import os

from werkzeug.security import check_password_hash, generate_password_hash

from app.repos import users as users_repo


def _normalize(username):
    """Normalize values for consistent comparisons."""
    return (username or "").strip().lower()


def _bootstrap_first_admin(username):
    # Single bootstrap path: first admin can be constrained with SHELF_BOOTSTRAP_ADMIN.
    if users_repo.has_any_admin():
        return False
    bootstrap_username = _normalize(os.environ.get("SHELF_BOOTSTRAP_ADMIN"))
    if bootstrap_username and username != bootstrap_username:
        return False
    users_repo.set_admin(username, True)
    return True


def register(username, password, age=None, gender=None):
    """Handle register for this module."""
    username = _normalize(username)
    existing = users_repo.get_by_username(username)
    if existing:
        # Allow claim if the account exists but has no password yet
        if not existing["password_hash"]:
            password_hash = generate_password_hash(password)
            users_repo.set_password_hash(username, password_hash)
            _bootstrap_first_admin(username)
            return {"username": username, "is_admin": users_repo.is_admin(username)}, None
        return None, "Username already exists"

    password_hash = generate_password_hash(password)
    users_repo.create_user(username, password_hash, age=age, gender=gender)
    _bootstrap_first_admin(username)
    return {"username": username, "is_admin": users_repo.is_admin(username)}, None


def login(username, password):
    """Handle login for this module."""
    username = _normalize(username)
    user = users_repo.get_by_username(username)
    if not user:
        return None, "Invalid username or password"

    stored_hash = user["password_hash"]
    if not stored_hash:
        return None, "Password not set for this user"

    if not check_password_hash(stored_hash, password):
        return None, "Invalid username or password"

    return {"username": user["username"].lower(), "is_admin": users_repo.is_admin(username)}, None


def change_password(username, current_password, new_password):
    """Change password after validation."""
    username = _normalize(username)
    user = users_repo.get_by_username(username)
    if not user:
        return "User not found"

    stored_hash = user["password_hash"]
    if not stored_hash:
        return "Password not set for this user"

    if not check_password_hash(stored_hash, current_password):
        return "Current password is incorrect"

    new_hash = generate_password_hash(new_password)
    users_repo.set_password_hash(username, new_hash)
    return None


def delete_account(username):
    """Delete account."""
    username = _normalize(username)
    user = users_repo.get_by_username(username)
    if not user:
        return "User not found"
    # Explicit policy: delete account and all related user-owned rows.
    users_repo.delete_user(username)
    return None
