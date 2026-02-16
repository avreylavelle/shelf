import importlib

import pytest


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """Create an isolated Flask test client backed by a temporary sqlite DB."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("MANGA_DB_PATH", str(db_path))
    monkeypatch.setenv("FLASK_DEBUG", "1")
    monkeypatch.setenv("FLASK_SECRET_KEY", "test-secret-key-0123456789")
    monkeypatch.delenv("SHELF_BOOTSTRAP_ADMIN", raising=False)

    # Clear shared recommendation caches so each test sees only its own fixture data.
    import app.services.recommendations as rec_service

    rec_service._MANGA_CACHE.clear()
    rec_service._OPTIONS_CACHE.clear()
    rec_service._STATS_NAME_CACHE.clear()

    import app.app as app_module

    app_module = importlib.reload(app_module)
    app = app_module.create_app()
    app.config.update(TESTING=True)

    with app.test_client() as client:
        yield app, client, db_path
