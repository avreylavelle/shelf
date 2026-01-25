import os
import sqlite3


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dataset_dir = os.path.join(base_dir, "Dataset")
    os.makedirs(dataset_dir, exist_ok=True)

    db_path = os.path.join(dataset_dir, "manga.db")
    schema_path = os.path.join(base_dir, "data", "schema.sql")

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()

    print(f"Initialized database at {db_path}")


if __name__ == "__main__":
    main()
