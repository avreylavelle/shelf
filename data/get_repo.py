from data.sqlite_repository import SqliteRepository

_REPO = None


def get_repo():
    global _REPO
    if _REPO is None:
        _REPO = SqliteRepository()
    return _REPO
