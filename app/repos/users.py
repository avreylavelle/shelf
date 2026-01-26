from app.db import get_db


def get_by_username(username):
    db = get_db()
    cur = db.execute("SELECT * FROM users WHERE username = ?", (username,))
    return cur.fetchone()


def create_user(username, password_hash, age=None, gender=None):
    db = get_db()
    db.execute(
        """
        INSERT INTO users (username, age, gender, preferred_genres, preferred_themes, password_hash)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (username, age, gender, "{}", "{}", password_hash),
    )
    db.commit()


def set_password_hash(username, password_hash):
    db = get_db()
    db.execute("UPDATE users SET password_hash = ? WHERE username = ?", (password_hash, username))
    db.commit()
