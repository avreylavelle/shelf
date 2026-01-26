from app.db import get_db
from utils.parsing import parse_dict


def get_profile(username):
    db = get_db()
    cur = db.execute(
        "SELECT username, age, gender, preferred_genres, preferred_themes FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "username": row["username"],
        "age": None if row["age"] is None else int(row["age"]),
        "gender": row["gender"] or "",
        "preferred_genres": parse_dict(row["preferred_genres"]),
        "preferred_themes": parse_dict(row["preferred_themes"]),
    }


def update_profile(username, age=None, gender=None):
    db = get_db()
    db.execute(
        "UPDATE users SET age = ?, gender = ? WHERE username = ?",
        (age, gender, username),
    )
    db.commit()


def update_username(old_username, new_username):
    db = get_db()
    db.execute(
        "UPDATE users SET username = ? WHERE username = ?",
        (new_username, old_username),
    )
    db.execute(
        "UPDATE user_ratings SET user_id = ? WHERE user_id = ?",
        (new_username, old_username),
    )
    db.commit()


def set_preferences(username, preferred_genres, preferred_themes):
    db = get_db()
    db.execute(
        "UPDATE users SET preferred_genres = ?, preferred_themes = ? WHERE username = ?",
        (str(preferred_genres), str(preferred_themes), username),
    )
    db.commit()


def clear_preferences(username):
    set_preferences(username, {}, {})
