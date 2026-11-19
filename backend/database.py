import os
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).resolve().parent / "planner.sqlite3"))
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'todo',
                event_date TEXT,
                notes TEXT NOT NULL DEFAULT '',
                image_url TEXT,
                image_source TEXT NOT NULL DEFAULT 'none',
                custom_fields TEXT NOT NULL DEFAULT '{}',
                view_config TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(plans)")}
        migrations = {
            "image_source": "ALTER TABLE plans ADD COLUMN image_source TEXT NOT NULL DEFAULT 'none'",
            "custom_fields": "ALTER TABLE plans ADD COLUMN custom_fields TEXT NOT NULL DEFAULT '{}'",
            "view_config": "ALTER TABLE plans ADD COLUMN view_config TEXT NOT NULL DEFAULT '{}'",
        }
        for column, statement in migrations.items():
            if column not in columns:
                connection.execute(statement)
        if "image_source" not in columns:
            connection.execute("UPDATE plans SET image_source = CASE WHEN image_url IS NULL THEN 'none' ELSE 'url' END")
        else:
            connection.execute("UPDATE plans SET image_source = CASE WHEN image_url IS NULL THEN 'none' ELSE 'url' END WHERE image_source IS NULL OR image_source = ''")


def reset_database() -> None:
    with get_connection() as connection:
        connection.execute("DROP TABLE IF EXISTS plans")
    initialize_database()
