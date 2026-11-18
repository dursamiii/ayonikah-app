from pathlib import Path
import sqlite3


DATABASE_PATH = Path(__file__).resolve().parent / "planner.sqlite3"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                event_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                image_url TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def reset_database() -> None:
    with get_connection() as connection:
        connection.execute("DROP TABLE IF EXISTS plans")
    initialize_database()
