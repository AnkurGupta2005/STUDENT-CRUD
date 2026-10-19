"""SQLite connection handling and schema creation.

The database file location comes from the STUDENTS_DB environment variable
(default: ./students.db) and is read on every call, which keeps the tests
simple: they just point it at a temporary file.
"""
import os
import sqlite3
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    date_of_birth   TEXT NOT NULL,           -- ISO date, YYYY-MM-DD
    email           TEXT UNIQUE,             -- stored lower-case, NULL allowed
    phone           TEXT,
    course          TEXT,
    address         TEXT,
    enrollment_date TEXT,                    -- ISO date, YYYY-MM-DD
    CHECK (email IS NOT NULL OR phone IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_students_course ON students(course);
CREATE INDEX IF NOT EXISTS idx_students_dob ON students(date_of_birth);
"""


def get_db_path() -> str:
    return os.getenv("STUDENTS_DB", "students.db")


def connect() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may set up a dependency in one worker
    # thread and run the endpoint in another. Each request gets its own
    # connection, so nothing is shared between threads.
    conn = sqlite3.connect(get_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: one connection per request, always closed."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
