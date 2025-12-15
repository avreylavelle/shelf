from utils.parsing import parse_list
import pandas as pd

# Creates a list of all unique genres and themes (or whatever)
def get_all_unique(df, column_name):
    unique_items = set()

    for entry in df[column_name].apply(parse_list):
        for item in entry:
            unique_items.add(item.strip())

    return sorted(unique_items)

# From the history of the dictionary, find the most frequently used genres and themes
def pick_top_from_counts(counts: dict, top_n: int):
    # Convert the dictionary into a list of (key, count) pairs
    items = []
    for key in counts: # iterate through values, add them to items
        items.append((key, counts[key]))

    # Sort by most to least frequent (integer value representing each theme or genre ^^^)
    items.sort(key=lambda x: x[1], reverse=True)

    # Get the most frequent
    top_keys = []
    for i in range(min(top_n, len(items))):
        top_keys.append(items[i][0])

    return top_keys

def filter_manga_by_score_range(manga_df, min_score=0.0, max_score=10.0):
    df = manga_df.copy()

    # Ensure score column is numeric
    df["score"] = pd.to_numeric(df.get("score", 0), errors = "coerce").fillna(0)

    # Filter based on score range provided by ui
    filtered = df[(df["score"] >= min_score) & (df["score"] <= max_score)]
    return filtered

def filter_manga_by_chapter_count(manga_df, min_chapters=0, max_chapters=10000):
    df = manga_df.copy()

    # Ensure chapters column is numeric
    df["chapters"] = pd.to_numeric(df.get("chapters", 0), errors = "coerce").fillna(0)

    # Filter based on chapter count range provided by ui
    filtered = df[(df["chapters"] >= min_chapters) & (df["chapters"] <= max_chapters)]
    return filtered

def filter_manga_by_status(manga_df, status_list):
    df = manga_df.copy()

    # If status is finished then filter by chapter count
    #todo

    return df