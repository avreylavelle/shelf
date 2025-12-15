from difflib import get_close_matches
from utils.parsing import parse_dict
from utils.cleaning import USER_PATH
import pandas as pd

# Taking in the database and username, determine if the profile exists.
# If it does, return all fields
def get_profile(user_df, username):
    row = user_df[user_df["username"] == username] # grab username
    if row.empty:
        return None # return if blank
    
    row = row.iloc[0]

    return { # return all values for the username, for the profile
        "username": row["username"],
        "age": None if pd.isna(row["age"]) else int(row["age"]),
        "gender": row["gender"] if isinstance(row["gender"], str) else "",
        "preferred_genres": parse_dict(row["preferred_genres"]),
        "preferred_themes": parse_dict(row["preferred_themes"]),
        "read_manga": parse_dict(row["read_manga"]),
    } 

# Removes old entries and updates with new entries
def update_user_profile(user_df, profile, user_path = USER_PATH):
    username = profile["username"]

    # Remove the previous profile
    user_df = user_df[user_df["username"] != username].copy()

    new_row = { # All updated values
        "username": username,
        "age": profile.get("age", ""),
        "gender": profile.get("gender", ""),
        "preferred_genres": str(profile.get("preferred_genres", {})),
        "preferred_themes": str(profile.get("preferred_themes", {})),
        "read_manga": str(profile.get("read_manga", {})),
    }

    # concat the new_row into the df, then put it to csv
    user_df = pd.concat([user_df, pd.DataFrame([new_row])], ignore_index=True)
    user_df.to_csv(user_path, index=False)
    return user_df

# Found this online for a username recommender, if its close but not quite
def similar_username(user_df, username, n=3, cutoff = 0.7):
    existing = user_df["username"].dropna().astype(str).tolist() # Makes a list of all current usernames
    return get_close_matches(username, existing, n=n, cutoff=cutoff) # returns any matches that are close 
