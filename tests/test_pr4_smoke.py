import sqlite3


def _insert_user(conn, username, is_admin=0):
    conn.execute(
        """
        INSERT INTO users (
            username,
            language,
            ui_prefs,
            preferred_genres,
            preferred_themes,
            blacklist_genres,
            blacklist_themes,
            signal_genres,
            signal_themes,
            is_admin
        )
        VALUES (?, 'English', '{}', '{}', '{}', '{}', '{}', '{}', '{}', ?)
        """,
        (username, 1 if is_admin else 0),
    )


def _seed_minimal_catalog(conn):
    conn.executemany(
        """
        INSERT INTO manga_core (
            id,
            link,
            title_name,
            english_name,
            japanese_name,
            synonymns,
            item_type,
            volumes,
            chapters,
            status,
            publishing_date,
            authors,
            serialization,
            genres,
            themes,
            demographic,
            description,
            content_rating,
            original_language,
            cover_url,
            links,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "mdx-action",
                "https://mangadex.org/title/mdx-action",
                "Action Story",
                "Action Story",
                None,
                "[]",
                "Manga",
                "10",
                "100",
                "Finished",
                "2020",
                "['Author A']",
                None,
                "['Action', 'Adventure']",
                "['School']",
                None,
                "Action title",
                "safe",
                "ja",
                None,
                "{}",
                "2025-01-01T00:00:00",
            ),
            (
                "mdx-romance",
                "https://mangadex.org/title/mdx-romance",
                "Romance Story",
                "Romance Story",
                None,
                "[]",
                "Manga",
                "8",
                "80",
                "Finished",
                "2019",
                "['Author B']",
                None,
                "['Romance']",
                "['Drama']",
                None,
                "Romance title",
                "safe",
                "ja",
                None,
                "{}",
                "2024-01-01T00:00:00",
            ),
        ],
    )

    conn.executemany(
        "INSERT INTO manga_map (mangadex_id, mal_id, match_method) VALUES (?, ?, ?)",
        [
            ("mdx-action", 1001, "test_seed"),
            ("mdx-romance", 1002, "test_seed"),
        ],
    )

    conn.executemany(
        """
        INSERT INTO manga_stats (
            mal_id,
            title_name,
            english_name,
            score,
            popularity,
            members,
            favorited,
            item_type,
            genres,
            themes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (1001, "Action Story", "Action Story", 8.8, 50, 120000, 9000, "Manga", "['Action', 'Adventure']", "['School']"),
            (1002, "Romance Story", "Romance Story", 8.0, 150, 50000, 4000, "Manga", "['Romance']", "['Drama']"),
        ],
    )


def _count_rows(conn, table, column, value):
    row = conn.execute(
        f"SELECT COUNT(*) FROM {table} WHERE lower({column}) = lower(?)",
        (value,),
    ).fetchone()
    return int(row[0])


def test_admin_gate_behavior(app_client):
    _, client, db_path = app_client

    with sqlite3.connect(db_path) as conn:
        _insert_user(conn, "admin_user", is_admin=1)
        _insert_user(conn, "regular_user", is_admin=0)
        conn.commit()

    with client.session_transaction() as session_state:
        session_state["user_id"] = "regular_user"
    response = client.get("/shelf/api/admin/model-snapshot")
    assert response.status_code == 403

    with client.session_transaction() as session_state:
        session_state["user_id"] = "admin_user"
    response = client.get("/shelf/api/admin/model-snapshot")
    assert response.status_code == 200
    payload = response.get_json()
    assert "snapshot" in payload


def test_rename_and_delete_consistency(app_client):
    _, client, db_path = app_client

    with sqlite3.connect(db_path) as conn:
        _insert_user(conn, "olduser", is_admin=0)
        conn.execute(
            """
            INSERT INTO user_ratings (user_id, manga_id, canonical_id, mdex_id, mal_id, rating, recommended_by_us, finished_reading)
            VALUES ('olduser', 'mdx-action', 'mdx-action', 'mdx-action', 1001, 9, 0, 0)
            """
        )
        conn.execute(
            """
            INSERT INTO user_dnr (user_id, manga_id, canonical_id, mdex_id, mal_id)
            VALUES ('olduser', 'mdx-romance', 'mdx-romance', 'mdx-romance', 1002)
            """
        )
        conn.execute(
            """
            INSERT INTO user_reading_list (user_id, manga_id, canonical_id, mdex_id, mal_id, status)
            VALUES ('olduser', 'mdx-action', 'mdx-action', 'mdx-action', 1001, 'Plan to Read')
            """
        )
        conn.execute(
            """
            INSERT INTO user_events (user_id, manga_id, event_type, event_value)
            VALUES ('olduser', 'mdx-action', 'clicked', 1.0)
            """
        )
        conn.execute(
            """
            INSERT INTO user_requests (user_id, genres, themes, blacklist_genres, blacklist_themes)
            VALUES ('olduser', '[]', '[]', '[]', '[]')
            """
        )
        conn.execute(
            """
            INSERT INTO user_request_cache (user_id, request_count, preferred_genres, preferred_themes, blacklist_genres, blacklist_themes)
            VALUES ('olduser', 1, '{}', '{}', '{}', '{}')
            """
        )
        conn.commit()

    with client.session_transaction() as session_state:
        session_state["user_id"] = "olduser"

    response = client.put("/shelf/api/profile", json={"username": "newuser"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["profile"]["username"] == "newuser"

    with sqlite3.connect(db_path) as conn:
        assert _count_rows(conn, "users", "username", "olduser") == 0
        assert _count_rows(conn, "users", "username", "newuser") == 1
        for table in ("user_ratings", "user_dnr", "user_reading_list", "user_events", "user_requests", "user_request_cache"):
            assert _count_rows(conn, table, "user_id", "olduser") == 0
            assert _count_rows(conn, table, "user_id", "newuser") == 1

    with client.session_transaction() as session_state:
        session_state["user_id"] = "newuser"
    response = client.post("/shelf/api/auth/delete-account")
    assert response.status_code == 200

    with sqlite3.connect(db_path) as conn:
        assert _count_rows(conn, "users", "username", "newuser") == 0
        for table in ("user_ratings", "user_dnr", "user_reading_list", "user_events", "user_requests", "user_request_cache"):
            assert _count_rows(conn, table, "user_id", "newuser") == 0


def test_recommendations_endpoint_basic_behavior(app_client):
    _, client, db_path = app_client

    with sqlite3.connect(db_path) as conn:
        _insert_user(conn, "reader", is_admin=0)
        _seed_minimal_catalog(conn)
        conn.commit()

    with client.session_transaction() as session_state:
        session_state["user_id"] = "reader"

    response = client.post(
        "/shelf/api/recommendations",
        json={"genres": ["Action"], "themes": []},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload.get("items"), list)
    assert payload["items"]
    ids = {item.get("id") for item in payload["items"]}
    assert "mdx-action" in ids


def test_browse_route_reuses_recommendation_cache(app_client, monkeypatch):
    _, client, db_path = app_client

    with sqlite3.connect(db_path) as conn:
        _insert_user(conn, "browser", is_admin=0)
        _seed_minimal_catalog(conn)
        conn.commit()

    with client.session_transaction() as session_state:
        session_state["user_id"] = "browser"

    # Warm cache once.
    first = client.get("/shelf/api/manga/browse")
    assert first.status_code == 200

    import app.services.recommendations as rec_service

    def fail_if_reload(*_args, **_kwargs):
        raise AssertionError("browse route reloaded manga dataframe instead of using cache")

    monkeypatch.setattr(rec_service, "_load_manga_df", fail_if_reload)
    second = client.get("/shelf/api/manga/browse")
    assert second.status_code == 200
