"""Helpers for extracting unique option values from dataframe columns."""

from utils.parsing import parse_list

# Creates a list of all unique genres and themes (or whatever)
def get_all_unique(df, column_name):
    """Return all unique."""
    unique_items = set()

    for entry in df[column_name].apply(parse_list):
        for item in entry:
            unique_items.add(item.strip())

    return sorted(unique_items)
