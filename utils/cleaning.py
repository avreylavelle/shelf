# Dataset Operations
import pandas as pd
import os 
import json

from utils.lookup import get_all_unique
from utils.parsing import parse_list

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(THIS_DIR)
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")

USER_PATH = os.path.join(DATASET_DIR, "user_data.csv")
CLEANED_PATH = os.path.join(DATASET_DIR, "cleaned_manga_entries.csv")
INPUT_PATH = os.path.join(DATASET_DIR, "manga_entries.csv")
ML_PATH = os.path.join(DATASET_DIR, "ml_cleaned_manga_entries.csv")
# USER_PATH_ML = os.path.join(DATASET_DIR, "user_data_ml.csv")
FEATURESET_PATH = os.path.join(DATASET_DIR, "ml_feature_set.csv")

# The three following functions are for cleaning / loading all of the csv files needed.
def clean_manga_dataset(input_path=INPUT_PATH, output_path=CLEANED_PATH):

    df = pd.read_csv(input_path)

    #Remove columns 13 (german name), 14 (french name), 15 (spanish name) since they had mixed data types and are not needed
    #Remove columns 26 (description) and 27 (background) since they contain large text data that is not needed for analysis 
    df.drop(df.columns[[12, 13, 14, 25, 26]], axis=1, inplace=True)

    #Save cleaned dataframe to new CSV file, rewrite existing cleaned file if it exists
    df.to_csv(output_path, index=False)

    return df

def clean_ml_manga_dataset(input_path=INPUT_PATH, output_path=ML_PATH):

    df = pd.read_csv(input_path)

    # Remove columns 2 and 3 (link and name) not needed for ml
    # Remove columns 10 (Synonyms), 11 (Japanese Name) 12 (English Name), 13 (german name), 14 (french name), 15 (spanish name) 
    # Remove columns 16, 17, 18, 19, 20(Chapters/status/publishing/Authors) - Cannot be used for determining
    # Remove column  25 (Demographic), not used for this (Can be filtered back in later)
    # Remove columns 26 (description) and 27 (background) since they contain large text data that is not needed for analysis 
    df.drop(df.columns[[1, 9, 10, 12, 13, 14, 15, 16, 17, 18, 19, 20, 25, 26]], axis=1, inplace=True)

    # Expand columns 21, 22, 23, 24 (Authors, Serialization, Genres, Themes) into separate features
    #Save cleaned dataframe to new CSV file, rewrite existing cleaned file if it exists
    df.to_csv(output_path, index=False)

    return df

# turn lists into individual features
# Loads the cleaned data ^^^
def load_data(cleaned_path=CLEANED_PATH):
    if not os.path.exists(cleaned_path):
        clean_manga_dataset() # clean it
    df = pd.read_csv(cleaned_path) # load it

    return df 

# Load the user_data.csv
def load_user(user_path = USER_PATH):
    if not os.path.exists(user_path): # if it doesnt exist
        df = pd.DataFrame(columns=[ # create the headers for the file
            "username",
            "age",
            "gender",
            "preferred_genres",   
            "preferred_themes",   
            "read_manga" # todo At some point, id like to add a flag for if it was recommened by us       
        ])
        df.to_csv(user_path, index=False) # return it (will be blank if it was just made)
        return df
    # shouldnt be blank, but it could be if no user has been made yet
    return pd.read_csv(user_path)


def load_ml_data(cleaned_path=ML_PATH):
    if not os.path.exists(cleaned_path):
        clean_ml_manga_dataset() # clean it

    df = pd.read_csv(cleaned_path) # load it

    return df

def initialize_ml_dataset():

    df = load_ml_data()

    # authors = get_all_unique(df, "authors")
    df["genres"] = df["genres"].apply(parse_list)
    df["themes"] = df["themes"].apply(parse_list)
    df["serialization"] = df["serialization"].apply(parse_list)

    genre_vocab = sorted({g for glist in df["genres"] for g in glist})
    theme_vocab = sorted({t for tlist in df["themes"] for t in tlist})
    demo_vocab = sorted(df["demographic"].dropna().unique())

    serial_counts = {}
    for serial_list in df["serialization"]:
        for s in serial_list:
            serial_counts[s] = serial_counts.get(s, 0) + 1

    serial_vocab = sorted([s for s, c in serial_counts.items() if c >= 30])

    print(f"Genres: {len(genre_vocab)} | Themes: {len(theme_vocab)} | Serialization kept: {len(serial_vocab)} | Demographic: {len(demo_vocab)}")
    feature_rows = []

    for _, row in df.iterrows():

        features = {
            "title_name": row["title_name"],
            "score": row["score"]
        }

        genres = set(row["genres"])
        themes = set(row["themes"])
        serials = set(row["serialization"])
        demo = row.get("demographic", "")

        # One-hot genres
        for g in genre_vocab:
            features[f"genre_{g}"] = 1 if g in genres else 0

        # One-hot themes
        for t in theme_vocab:
            features[f"theme_{t}"] = 1 if t in themes else 0

        # One-hot serialization (pruned)
        for s in serial_vocab:
            features[f"serial_{s}"] = 1 if s in serials else 0

        # One-hot demographic
        for d in demo_vocab:
            features[f"demo_{d}"] = 1 if d == demo else 0

        feature_rows.append(features)

    feature_df = pd.DataFrame(feature_rows)

    feature_df.to_csv(FEATURESET_PATH, index=False)

def load_ml_featureset():
    if not os.path.exists(FEATURESET_PATH):
        initialize_ml_dataset()

    df = pd.read_csv(FEATURESET_PATH) # load it

    return df


def user_ml_dataset(profile):
    
    username = profile["username"]

    ml_dataset = load_ml_featureset()
    read_manga = profile.get("read_manga", {})

    rows = []

    for manga, rating in read_manga.items():
        matches = ml_dataset[ml_dataset["title_name"] == manga]

        if matches.empty:
            continue

        row = matches.iloc[0].copy()
        row["rating"] = float(rating)
        rows.append(row)

    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    
    if "score" in df.columns:
        df = df.drop(columns=["score"])

    out_path = os.path.join(DATASET_DIR, f"user_data_ml_{username}.csv")
    df.to_csv(out_path, index=False)

    print("Saved all CSVs.")

    return df
        
