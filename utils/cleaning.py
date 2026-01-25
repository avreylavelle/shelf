# Dataset Operations
import pandas as pd
import os

from utils.db import get_connection, table_exists, ensure_users_table

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(THIS_DIR)
DATASET_DIR = os.path.join(BASE_DIR, "Dataset")

MANGA_CLEANED_TABLE = "manga_cleaned"

# turn lists into individual features
# Loads the cleaned data ^^^
def load_data():
    with get_connection() as conn:
        if not table_exists(conn, MANGA_CLEANED_TABLE):
            raise FileNotFoundError(
                "Missing SQLite table 'manga_cleaned'. Import data into manga.db first."
            )
        df = pd.read_sql_query(f"SELECT * FROM {MANGA_CLEANED_TABLE}", conn)

    return df

# Load users from sqlite
def load_user():
    with get_connection() as conn:
        ensure_users_table(conn)
        df = pd.read_sql_query("SELECT * FROM users", conn)

    return df


