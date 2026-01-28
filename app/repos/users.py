from app.db import get_db


def get_by_username(username):
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE lower(username) = lower(?)", (username,))
    return cur.fetchone()


def create_user(username, password_hash, age=None, gender=None, language="English", ui_prefs="{}"):
    username = (username or "").strip().lower()
    db = get_db()
    db.execute(
        """
        INSERT INTO users (username, age, gender, language, ui_prefs, preferred_genres, preferred_themes, signal_genres, signal_themes, password_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (username, age, gender, language, ui_prefs, "{}", "{}", "{}", "{}", password_hash),
    )
    db.commit()


def set_password_hash(username, password_hash):
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE lower(username) = lower(?)", (password_hash, username))
    db.commit()


def delete_user(username):
    db = get_db()
    db.execute("DELETE FROM users WHERE lower(username) = lower(?)", (username,))
    db.commit()
