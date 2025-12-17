import os
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import mutual_info_regression
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from utils.cleaning import load_ml_featureset, user_ml_dataset, DATASET_DIR

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

    return results

def analyze_global_features():
    df = load_ml_featureset()

    df = df.dropna(subset=["score"])

    y = df["score"].astype(float)
    X = df.drop(columns=["title_name", "score"], errors='ignore')

    
    results = {}

    pearson = X.apply(lambda col: np.corrcoef(col, y)[0, 1])
    results['pearson'] = pearson.sort_values(ascending=False)

    mi = mutual_info_regression(X, y, random_state=42)
    results['mutual_info'] = pd.Series(mi, index=X.columns).sort_values(ascending=False)

    r2_scores = {}
    reg = LinearRegression()

    for col in X.columns:
        Xi = X[[col]]
        reg.fit(Xi, y)
        y_pred = reg.predict(Xi)
        r2 = r2_score(y, y_pred)
        r2_scores[col] = r2

    results["single_feature_r2"] = pd.Series(r2_scores).sort_values(ascending=False)

    rf = RandomForestRegressor(n_estimators=250, random_state=42, n_jobs=-1)
    rf.fit(X,y)
    results["rf_importances"] = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)

    results["variance"] = X.var().sort_values(ascending=False)

    return results

def analyze_user_features(profile):
    username = profile["username"]
    path = os.path.join(DATASET_DIR, f"user_data_ml_{username}.csv")

    if not os.path.exists(path):
        print(f"No user dataset found for {username}. Please generate the dataset first.")
        return None
    
    print(f"Analyzing features for user {username}...")

    df = pd.read_csv(path)

    y = df["rating"]
    X = df.drop(columns=["title_name", "rating"], errors='ignore')

    results = {}

    pearson = X.apply(lambda col: np.corrcoef(col, y)[0, 1])
    results['pearson'] = pearson.sort_values(ascending=False)

    mi = mutual_info_regression(X, y, random_state=42)
    results['mutual_info'] = pd.Series(mi, index=X.columns).sort_values(ascending=False)

    rf = RandomForestRegressor(n_estimators=250, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    results["rf_importances"] = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)

    print("Feature analysis complete.")
    return results