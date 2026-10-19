import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A client backed by a fresh, empty SQLite file for every test."""
    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "test.db"))
    with TestClient(app) as c:  # the `with` runs the startup hook (creates the table)
        yield c


def make_student(**overrides) -> dict:
    data = {
        "name": "Test Student",
        "date_of_birth": "2004-05-17",
        "email": "test.student@example.com",
        "phone": "+91 98765 43210",
        "course": "Computer Science",
        "address": "12 Example Road, Bhubaneswar",
        "enrollment_date": "2023-08-01",
    }
    data.update(overrides)
    return data
