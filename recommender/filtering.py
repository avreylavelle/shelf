from utils.parsing import parse_list


def filter_nsfw(df, profile):
    # Automatically turn off nsfw content for underage users (ie. genres with Ecchi, Hentai, etc)
    if profile.get("age") is not None and profile["age"] < 18:
        df = df[df["genres"].apply(
            lambda x: "Hentai" not in str(x) 
                    and "Ecchi" not in str(x) 
                    and "Erotica" not in str(x)
        )]
        if "content_rating" in df.columns:
            df = df[~df["content_rating"].fillna("").str.lower().isin({"erotica", "pornographic"})]
        
    return df

def parse_lists(df):
    df = df.copy()

    # Turn the genres and themes into python lists
    df["genres"] = df["genres"].apply(parse_list) 
    df["themes"] = df["themes"].apply(parse_list)

    return df

def filter_already_read(df, read_manga):
    # Exclude the already read titles
    if "id" in df.columns:
        df = df[~df["id"].isin(read_manga.keys())]
    else:
        df = df[~df["title_name"].isin(read_manga.keys())]

    return df

def filter_item_type(df, content_types=None):
    if not content_types:
        return df
    allowed = {str(t).strip() for t in content_types if str(t).strip()}
    if not allowed:
        return df
    available = set(df["item_type"].dropna().unique()) if "item_type" in df.columns else set()
    if available and not (allowed & available):
        return df
    return df[df["item_type"].isin(allowed)]

def filter_blacklist(df, blacklist_genres=None, blacklist_themes=None):
    blacklist_genres = [g for g in (blacklist_genres or []) if g]
    blacklist_themes = [t for t in (blacklist_themes or []) if t]
    if blacklist_genres:
        df = df[~df["genres"].apply(lambda values: any(g in values for g in blacklist_genres))]
    if blacklist_themes:
        df = df[~df["themes"].apply(lambda values: any(t in values for t in blacklist_themes))]
    return df


def run_filters(manga_df, profile, read_manga, content_types=None, blacklist_genres=None, blacklist_themes=None):
    """Apply all filtering steps."""

    df = manga_df.copy()

    df = filter_nsfw(df, profile)
    df = parse_lists(df)
    df = filter_blacklist(df, blacklist_genres, blacklist_themes)
    df = filter_already_read(df, read_manga)
    df = filter_item_type(df, content_types=content_types)

    return df
