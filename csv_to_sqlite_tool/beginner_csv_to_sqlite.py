import csv
import sqlite3
from pathlib import Path


def csv_to_sqlite(csv_file, db_file, table_name):
    csv_path = Path(csv_file)

    if not csv_path.exists():
        print(f"File not found: {csv_file}")
        return

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        headers = next(reader)

        columns_sql = ", ".join(f'"{column}" TEXT' for column in headers)
        columns_names = ", ".join(f'"{column}"' for column in headers)
        placeholders = ", ".join("?" for _ in headers)

        connection = sqlite3.connect(db_file)
        cursor = connection.cursor()

        cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        cursor.execute(f'CREATE TABLE "{table_name}" ({columns_sql})')

        for row in reader:
            cursor.execute(
                f'INSERT INTO "{table_name}" ({columns_names}) VALUES ({placeholders})',
                row,
            )

        connection.commit()
        connection.close()

    print("Done")
    print(f"CSV: {csv_file}")
    print(f"SQLite database: {db_file}")
    print(f"Table: {table_name}")


csv_to_sqlite(
    csv_file="examples/users.csv",
    db_file="examples/users_beginner.sqlite3",
    table_name="users",
)
