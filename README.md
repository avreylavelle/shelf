# Manga Recommender System (Content Based and Personalized ML)

This content based manga recommednation system was made with the intent to... Recommend manga. 
There are not many great manga recommenders out there, especially due to the nature of how these mangas are categorized. A very common example are using the genres "Action", "Adventure", "Fantasy", and so on. These genres apply to a lare quantity of mangas, and in no way dictate the actual quality, tone, feel, or how enjoyable a read it will be. 

Due to these limitations, I (We, this started as a group project and quickly became an indiviual passion project) decided that it would be best to try to find what features would be the best to automatically rank and recommend mangas on a per user basis. 

This code combines explicit user preferences, interperatable heurisitcs, and lighteight machine learning to personalize recommendations, without relying on large scale user behavior or any major black box models. 

This project is intended to explore how far content and metadata alone can go in the journey of recommending quality manga consistently, adapting overtime to reader tatse, and where its inevitable limitations stop it.

## Project Goals
 - Build a manga recommender that is not reliant on a massive user base
 - Support cold start users (Me, funnily enough I do not read very much)
 - Learn personalized preferecnes weights on a per user basis
 - Maintain its interpretability and explainaibitly, as to not become too complex
 - Explore limits

As mentioned before, this is a passion project. Simply for fun!

## Core Ideas

### 1. Content Based Recommendation

Recommendations are driven by manga metadata from a MyAnimeList dataset, such as:
 - Genres
 - Themes
 - Demographics
 - Serializaiton Source
 - Publicaiton context

### 2. Handwritten Heuristic Baseline

The first part of this project, and what essentially was the focus of the Final Project aspect for my school project was this:

A deterministic recommender scores manga using:
 - Genre overlap
 - Theme overlap
 - User history affinity
 - Rated title similarity

This baseline works very well for a cold start, when a user knows exactly what type of genres, or general vibe they are looking for. Using my roommate as a test dummy, (he reads a lot), It actually spit out some quality recommendations and was a driving force for the "passion" part of this project. It could always be better!

### 3. Machine Learning as Weight learner

The basis of this recommendation system is defined by a few weights, found in the recommender/constants.py file. These were handmade through talk with my groupmates and roommate.

Instead of replacing the core logic, I thought that using Machine Learning on user datasets to learn how much each signal matters per user, whether that be on a broad "genre" or "theme", or perhaps choosing specific themes and genres that are actually important to the model in its accuracy in determining manga scores.

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

Due to this, the current implementation cannot succeed the way I hope. A few ways to counteract this are perhaps:
 - Weighting with global ranks weighted as well, to generally recommend higher quality mangas
 - Recommending based on other users ratings (This requires a large userbase)
  - Perhaps, using global user data from larger websites

Overall, this project is research into how well content alone can succeed. 

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
