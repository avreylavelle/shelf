# Shelf — Manga Recommender (Content‑Based)

## Overview
Shelf is a content‑based manga recommender with **both a web app and a terminal UI**. It runs entirely on **SQLite**, emphasizes **interpretability**, and works without large‑scale collaborative data. The system combines metadata signals (genres, themes, demographics) with user history to rank recommendations.

The project currently ships with:
- **Web app (Flask + JS)** under `/shelf` with login, dashboard, ratings, recommendations, reading list, and DNR.
- **Terminal UI (TUI)** for the original CLI experience.
- **SQLite‑backed** data and user profiles, with a repository/service architecture.

## Key Features

### Web App
- **Auth + profiles** (age, gender, language)
- **Dashboard** with quick links
- **Recommendations** with:
  - Reroll
  - Diversity control
  - “Include less popular” toggle
  - Explainability badges
  - Personalized mode toggle
- **Ratings** CRUD + “recommended by us” + “finished reading”
- **Reading List** with status (Plan to Read / In Progress)
- **Do Not Recommend (DNR)** list
- **Admin tools** (user switch + CSV import/export)

### Personalization (Phase 2)
Signals are logged and converted into per‑user affinities:
- Rated titles
- Finished reading
- Clicked details
- Reading list
- DNR

These affinities lightly bias scoring when “Personalized” is enabled (with guardrails).

## Recommender Modes
- **v3 (Balanced)**: default. Original scoring blend + improved normalization and signal affinities.
- **v2 (Relative)**: min‑max normalizes match/internal within the current pool.
- **v1 (Legacy)**: original baseline scoring.

The web UI currently defaults to **v3**.

## How Recommendations Are Scored (High‑Level)
- Match score (requested genres/themes, history, rating affinities)
- Internal score (dataset score) scaled to 0–1
- Combined score (70% match / 30% internal)
- Optional diversity & novelty adjustments

## Project Structure
```
manga_recommender_ml/
  app/                 # Flask web app
    routes/            # API + auth
    services/          # Web services layer
    repos/             # DB access
    templates/         # HTML pages
    static/            # JS/CSS
  recommender/         # Core scoring + filtering
  core/                # Shared recommendation entrypoint
  ui_terminal/         # CLI/TUI interface
  Dataset/             # SQLite DB + dataset refs
  utils/               # Parsing/cleaning helpers
  main.py              # CLI entrypoint
  requirements.txt
```

## Running Locally

### 1) Create venv + install
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2) Run Terminal UI
```
python main.py
```

### 3) Run Web App (dev)
```
python app/app.py
```
Then open:
- `http://localhost:5000/shelf/login`

### 4) Run Web App (prod)
```
gunicorn -w 2 -b 127.0.0.1:5000 app.app:app
```

## Configuration
Environment variables:
- `MANGA_DB_PATH` — optional path to the SQLite DB (defaults to `Dataset/manga.db`)
- `FLASK_SECRET_KEY` — session secret
- `RECOMMENDER_MODE` — optional default mode (`v1`, `v2`, `v3`)

## Admin
- Admin user is currently hard‑coded as `avreylavelle`.
- Admin tools live at `/shelf/admin`.

## Notes
- The web app is designed to run under the `/shelf` base path (reverse‑proxy friendly).
- The system intentionally avoids heavy ML and focuses on interpretable, content‑based ranking.
- See `todo.txt` for the current roadmap.
