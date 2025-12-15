import pandas as pd
from utils.parsing import parse_list
from recommender.constants import (
    EARLIEST_DESIRED_DATE
)

def filter_nsfw(df, profile):
    # Automatically turn off nsfw content for underage users (ie. genres with Ecchi, Hentai, etc)
    if profile.get("age") is not None and profile["age"] < 18:
        df = df[df["genres"].apply(
            lambda x: "Hentai" not in str(x) 
                    and "Ecchi" not in str(x) 
                    and "Erotica" not in str(x)
        )]
        
    return df

def parse_lists(df):
    df = df.copy()

    # Turn the genres and themes into python lists
    df["genres"] = df["genres"].apply(parse_list) 
    df["themes"] = df["themes"].apply(parse_list)

    return df

def filter_already_read(df, profile):
    # Exclude the already read titles
    read_manga = profile.get("read_manga", {})
    df = df[~df["title_name"].isin(read_manga.keys())]

    return df

def publish_date_filter(df):
    
    def keep_row(date): # this does not recommend anything older than desired
        text = str(date).strip()
        last_piece = text.split()[-1] # last string in line

        if last_piece.endswith("?"): # publishing, its fine
            return True
        try:
            year = int(last_piece[:4])
            if year >= EARLIEST_DESIRED_DATE: # if its newer
                return True # good
            else: # older
                return False # bad
        except:
            return True
        
    return df[df["publishing_date"].apply(keep_row)]

def filter_item_type():
    # Doujinshi,  Light Novel,  Manga,  Manhua,  Manhwa,  Novel,  One-shot
    pass

def run_filters(manga_df, profile):
    """Apply all filtering steps."""

    df = manga_df.copy()

    df = filter_nsfw(df, profile)
    df = parse_lists(df)
    df = filter_already_read(df, profile)
    df = publish_date_filter(df)

    return df
