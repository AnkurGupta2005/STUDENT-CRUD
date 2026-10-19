"""Database access for students. Every query is parameterised."""
import sqlite3
from datetime import date
from typing import Optional

from .schemas import StudentCreate

COLUMNS = ("name", "date_of_birth", "email", "phone", "course", "address", "enrollment_date")


class DuplicateEmailError(Exception):
    pass


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _values(data: StudentCreate) -> tuple:
    return (
        data.name,
        data.date_of_birth.isoformat(),
        data.email,
        data.phone,
        data.course,
        data.address,
        data.enrollment_date.isoformat() if data.enrollment_date else None,
    )


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def create_student(conn: sqlite3.Connection, data: StudentCreate) -> dict:
    try:
        cur = conn.execute(
            f"INSERT INTO students ({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
            _values(data),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "email" in str(exc).lower():
            raise DuplicateEmailError(data.email) from exc
        raise
    return get_student(conn, cur.lastrowid)


def get_student(conn: sqlite3.Connection, student_id: int) -> Optional[dict]:
    row = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_students(
    conn: sqlite3.Connection,
    *,
    name: Optional[str] = None,
    course: Optional[str] = None,
    email: Optional[str] = None,
    born_after: Optional[date] = None,
    born_before: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[dict]:
    clauses: list[str] = []
    params: list = []

    if name:
        clauses.append("name LIKE ? ESCAPE '\\' COLLATE NOCASE")
        params.append(f"%{_escape_like(name.strip())}%")
    if course:
        clauses.append("course LIKE ? ESCAPE '\\' COLLATE NOCASE")
        params.append(f"%{_escape_like(course.strip())}%")
    if email:
        clauses.append("email = ?")
        params.append(email.strip().lower())
    if born_after:
        clauses.append("date_of_birth > ?")
        params.append(born_after.isoformat())
    if born_before:
        clauses.append("date_of_birth < ?")
        params.append(born_before.isoformat())

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = conn.execute(
        f"SELECT * FROM students {where} ORDER BY id LIMIT ? OFFSET ?",
        (*params, limit, skip),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def count_students(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]


def update_student(conn: sqlite3.Connection, student_id: int, data: StudentCreate) -> Optional[dict]:
    try:
        cur = conn.execute(
            f"UPDATE students SET {', '.join(c + ' = ?' for c in COLUMNS)} WHERE id = ?",
            (*_values(data), student_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if "email" in str(exc).lower():
            raise DuplicateEmailError(data.email) from exc
        raise
    if cur.rowcount == 0:
        return None
    return get_student(conn, student_id)


def delete_student(conn: sqlite3.Connection, student_id: int) -> bool:
    cur = conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    return cur.rowcount > 0
