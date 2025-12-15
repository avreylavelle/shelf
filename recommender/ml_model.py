import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from utils.cleaning import load_ml_featureset, user_ml_dataset

MODEL_DIR = "Dataset/models"

def model_path(username):
    os.makedirs(MODEL_DIR, exist_ok=True)
    return os.path.join(MODEL_DIR, f"{username}_model.pkl")

def train_user_model(profile):

    username = profile["username"]
    
    df =user_ml_dataset(profile)
    
    if df is None or df.empty:
        print(f"No training data available for user {username}.")
        return
    
    y = df["rating"]
    X = df.drop(columns=["title_name", "rating"])

    model = RandomForestRegressor(n_estimators=250, random_state=42, n_jobs=-1)

    print(f"Training model for user {username}...")
    model.fit(X, y)
    print(f"Model training complete for user {username}.")

    joblib.dump(model, model_path(username))

    return model    

def recommend_for_user(profile, top_n=20):

    username = profile["username"]
    path = model_path(username)

    if not os.path.exists(path):
        print(f"No trained model found for user {username}. Please train a model first.")
        return None
    
    model = joblib.load(path)
    ml_df = load_ml_featureset()

    read_titles = set(profile.get("read_manga", {}).keys())
    unread = ml_df[~ml_df["title_name"].isin(read_titles)].copy()

    X = unread.drop(columns=["title_name", "score"])
    unread["predicted_rating"] = model.predict(X)

    results = unread.sort_values("predicted_rating", ascending=False)

    print(results.head(top_n))
