from werkzeug.security import check_password_hash, generate_password_hash

from app.repos import users as users_repo


def register(username, password, age=None, gender=None):
    existing = users_repo.get_by_username(username)
    if existing:
        if not existing["password_hash"]:
            password_hash = generate_password_hash(password)
            users_repo.set_password_hash(username, password_hash)
            return {"username": username}, None
        return None, "Username already exists"

    password_hash = generate_password_hash(password)
    users_repo.create_user(username, password_hash, age=age, gender=gender)
    return {"username": username}, None


def login(username, password):
    user = users_repo.get_by_username(username)
    if not user:
        return None, "Invalid username or password"

    stored_hash = user["password_hash"]
    if not stored_hash:
        return None, "Password not set for this user"

    if not check_password_hash(stored_hash, password):
        return None, "Invalid username or password"

    return {"username": user["username"]}, None


def change_password(username, current_password, new_password):
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
