# Manga Recommender System (Content Based)

## Overview 

This project implements a content-based manga recommendation system that personalizes rankings using metadata-driven signals. Unlike collaborative filtering approaches, this system operates without a large user base, supports cold-start users, and emphasizes interpretability over black-box models.

The recommender combines explicit user preferences and heuristic scoring to adapt recommendations over time using content and metadata alone. Storage is SQLite-based, and all data access is routed through a repository interface.

## Project Goals
 - Operate without large-scale user behavior data
 - Support cold-start users
 - Track per-user preference signals
 - Maintain interpretability and explainability
 - Explore the practical limits of content-based recommendation

## Core Ideas

### 1. Content Based Recommendation

Recommendations are driven by manga metadata from a MyAnimeList dataset, such as:

 - Genres
 - Themes
 - Demographics
 - Serializaiton Source
 - Publicaiton context

### 2. Handwritten Heuristic Baseline

A deterministic recommender scores manga using:

 - Genre overlap
 - Theme overlap
 - User history affinity
 - Rated title similarity

This baseline provides strong cold-start performance and serves as a fallback when insufficient user data is available.

## System Architecture

The overall system architecture is:
UI -> Services -> Repository -> SQLite
Profile -> Signal Extraction -> Final Ranking -> Recommend

## Signals Used:

Signals intended for use:
 - Requested genre overlap (optional)
 - Requested theme overlap (optional)
 - Historical genre affinity
 - Historical theme affinity
 - Rated title genre affinity
 - Rated title theme affinity
 - Serializaiton match
 - Demographic match
 - Global feature quality score

These signals are combined deterministically in the scoring logic.


## Limitations

I can see a few things happening with this model in the end
 - No collaborative filtering
 - No large scale behavioral data
 - No embeddings or deep learning
 - Metadata **CANNOT** capture tone, quality, or emotional impact

This project intentionally explores how far content-only recommendation can go, and where it breaks down.

## Project Structure

manga_recommender_ml/
  Dataset/
    dataset.txt
    manga.db
  recommender/
    constants.py
    filtering.py
    recommender.py
    scoring.py
  core/
    recommendations.py
  data/
    repository.py
    sqlite_repository.py
    get_repo.py
    schema.sql
  services/
    library.py
    recommendations.py
  ui_terminal/
    tui_menu.py
    tui_profile.py
    tui_recommend.py
  user/
    user_profile.py
  utils/
    cleaning.py
    input.py
    lookup.py
    parsing.py
  main.py
  README.md
  requirements.txt

## Running the project

### 1. Clone the repository
 - Navigate to preferred directory
 - git clone https://github.com/avreylavelle/manga_recommender_ml.git
 - cd manga_recommender_ml
 - 
### 2. Create venv
 - python -m venv venv
 - source venv/Scripts/activate (This is git bash on windows. Use proper commands for OS and terminal)

### 3. Install dependencies
 - pip install -r requirements.txt

### 4. Run
 - python main.py

## User Experience

### As of right now, it is as follows:

The user can create and then sign into a profile, recommend themselves manga, and rate manga.
