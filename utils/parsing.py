"""Safe parsing helpers for list/dict values read from storage."""

import ast
import pandas as pd
# Parse lists from the dataset into python lists
def parse_list(val):
    """Parse list into normalized data."""
    if isinstance(val, str): # if its a string
        try:
            return ast.literal_eval(val) # return it
        except Exception:
            # If it's just comma-separated text
            items = []
            for x in val.split(","): # split it
                x = x.strip() # strip whitespace
                if x:
                    items.append(x) # add it to x, as a list
            return items  
    elif isinstance(val, list): # if its already a list, return it
        return val
    return []

# Here I am deciding to use dicts serialized as strings to store user data
# However, its a bit tricky since dicts dont store super easily, so I need to parse them properly
# I could use other methods that would probably be easier, but im trying to keep it consistent
def parse_dict(val):
    # If its a real dictonary, return it 
    if isinstance(val, dict):
        return val
    # if its blank
    if pd.isna(val) or val is None:
        return {}
    # return strings
    try:
        return ast.literal_eval(val)
    # if the parsing fails for any reason, return empty
    except:
        return {}
    
