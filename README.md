# Manga Recommender System (Content Based and Personalized ML)

## Overview 

This project implements a content-based manga recommendation system that personalizes rankings using metadata-driven signals and lightweight machine learning. Unlike collaborative filtering approaches, this system operates without a large user base, supports cold-start users, and emphasizes interpretability over black-box models.

The recommender combines explicit user preferences, heuristic scoring, and per-user machine learning to adapt recommendations over time using content and metadata alone.

## Project Goals
 - Operate without large-scale user behavior data
 - Support cold-start users
 - Learn per-user preference weights
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

### 3. Machine Learning as Weight learner

Rather than replacing the scoring logic, machine learning is used to learn how much each signal matters per user.

 - Signals are explicitly defined (From the MAL dataset)
 - Model learns weights, not the overarching structure
 - Models are trained per user, not per dataset
 - Fallback to the heuristic with data is insufficient
 - 
## System Architecture

The overall system architecutre is hoped to be followed as such:
Profile -> Signal Extraction -> Learn weights -> Final Ranking -> Recommend / explain (if requested)

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

These signals should be sufficient training inputs for the model.

### Machine Learning Models:

As mentioned before, this is is intended on a per user basis. Therefore, using simple, stable, quick models is the intent.

Ridge Regression
 - Should learn stable per user weights
 - Handles correlated signals well
Lasso Regression
 - Identifies the overall importance of signals
 - Enables feature pruning
Random Forest
 - Used for feature important analysis

## Feature Analysis

The system supports Global feature analysis, per user feature analysis, and many others to be added later. This is simply for analysis and research.

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
    user_data.csv
  recommender/
    constants.py
    filtering.py
    ml_model.py
    recommender.py
    scoring.py
  ui_terminal/
    tui_machinelearning.py
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

The user can create and then sign into a profile, recommend themselves manga, and rate manga. The machine learning menu is also available.
