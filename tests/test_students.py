from .conftest import make_student


# ---------- Create ----------
def test_create_student(client):
    r = client.post("/students", json=make_student())
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["name"] == "Test Student"
    assert body["email"] == "test.student@example.com"


def test_ids_are_unique_and_increment(client):
    a = client.post("/students", json=make_student(email="a@example.com")).json()
    b = client.post("/students", json=make_student(email="b@example.com")).json()
    assert a["id"] != b["id"]


def test_create_with_only_required_fields(client):
    r = client.post("/students", json={"name": "Min", "date_of_birth": "2001-01-01", "phone": "9876543210"})
    assert r.status_code == 201
    assert r.json()["course"] is None


def test_email_is_normalised_to_lowercase(client):
    r = client.post("/students", json=make_student(email="  MiXed@Example.COM "))
    assert r.json()["email"] == "mixed@example.com"


def test_duplicate_email_rejected(client):
    client.post("/students", json=make_student())
    r = client.post("/students", json=make_student(name="Someone Else", email="TEST.student@example.com"))
    assert r.status_code == 409


# ---------- Validation ----------
def test_missing_required_field(client):
    r = client.post("/students", json={"date_of_birth": "2004-05-17", "email": "x@example.com"})
    assert r.status_code == 422


def test_needs_email_or_phone(client):
    r = client.post("/students", json={"name": "No Contact", "date_of_birth": "2004-05-17"})
    assert r.status_code == 422


def test_invalid_email(client):
    assert client.post("/students", json=make_student(email="not-an-email")).status_code == 422


def test_invalid_phone(client):
    assert client.post("/students", json=make_student(phone="abc")).status_code == 422


def test_invalid_date_format(client):
    assert client.post("/students", json=make_student(date_of_birth="17/05/2004")).status_code == 422


def test_future_date_of_birth(client):
    assert client.post("/students", json=make_student(date_of_birth="2999-01-01")).status_code == 422


def test_blank_name(client):
    assert client.post("/students", json=make_student(name="   ")).status_code == 422


def test_enrollment_before_birth(client):
    r = client.post("/students", json=make_student(enrollment_date="2000-01-01"))
    assert r.status_code == 422


# ---------- Read ----------
def test_get_student(client):
    sid = client.post("/students", json=make_student()).json()["id"]
    r = client.get(f"/students/{sid}")
    assert r.status_code == 200
    assert r.json()["id"] == sid


def test_get_missing_student_404(client):
    r = client.get("/students/999")
    assert r.status_code == 404
    assert "999" in r.json()["detail"]


def test_get_non_integer_id_422(client):
    assert client.get("/students/abc").status_code == 422


def test_list_empty(client):
    r = client.get("/students")
    assert r.status_code == 200 and r.json() == []


def test_list_and_filters(client):
    client.post("/students", json=make_student(name="Aarav Sharma", email="aarav@example.com",
                                               date_of_birth="2004-05-17", course="Computer Science"))
    client.post("/students", json=make_student(name="Diya Patel", email="diya@example.com",
                                               date_of_birth="2006-02-10", course="Mechanical Engineering"))
    client.post("/students", json=make_student(name="Rohan Das", email="rohan@example.com",
                                               date_of_birth="2001-11-30", course="Computer Science"))

    assert len(client.get("/students").json()) == 3
    assert [s["name"] for s in client.get("/students", params={"course": "computer"}).json()] == \
        ["Aarav Sharma", "Rohan Das"]
    assert [s["name"] for s in client.get("/students", params={"name": "DIYA"}).json()] == ["Diya Patel"]
    assert [s["name"] for s in client.get("/students", params={"email": "rohan@example.com"}).json()] == \
        ["Rohan Das"]
    assert [s["name"] for s in client.get("/students", params={"born_after": "2005-12-31"}).json()] == \
        ["Diya Patel"]
    assert [s["name"] for s in client.get("/students", params={"born_before": "2002-01-01"}).json()] == \
        ["Rohan Das"]
    both = client.get("/students", params={"course": "computer", "born_after": "2003-01-01"}).json()
    assert [s["name"] for s in both] == ["Aarav Sharma"]


def test_filter_wildcards_are_literal(client):
    client.post("/students", json=make_student())
    assert client.get("/students", params={"name": "%"}).json() == []


def test_pagination(client):
    for i in range(5):
        client.post("/students", json=make_student(name=f"S{i}", email=f"s{i}@example.com"))
    page = client.get("/students", params={"skip": 2, "limit": 2}).json()
    assert [s["name"] for s in page] == ["S2", "S3"]


def test_bad_pagination_rejected(client):
    assert client.get("/students", params={"limit": 0}).status_code == 422
    assert client.get("/students", params={"skip": -1}).status_code == 422


# ---------- Update ----------
def test_put_replaces_student(client):
    sid = client.post("/students", json=make_student()).json()["id"]
    r = client.put(f"/students/{sid}", json=make_student(name="Renamed", course=None))
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"
    assert r.json()["course"] is None


def test_put_missing_404(client):
    assert client.put("/students/42", json=make_student()).status_code == 404


def test_put_duplicate_email_409(client):
    client.post("/students", json=make_student(email="one@example.com"))
    two = client.post("/students", json=make_student(email="two@example.com")).json()
    r = client.put(f"/students/{two['id']}", json=make_student(email="one@example.com"))
    assert r.status_code == 409


def test_patch_changes_only_sent_fields(client):
    sid = client.post("/students", json=make_student()).json()["id"]
    r = client.patch(f"/students/{sid}", json={"course": "Physics"})
    assert r.status_code == 200
    body = r.json()
    assert body["course"] == "Physics"
    assert body["name"] == "Test Student"          # untouched
    assert body["email"] == "test.student@example.com"


def test_patch_persists(client):
    sid = client.post("/students", json=make_student()).json()["id"]
    client.patch(f"/students/{sid}", json={"phone": "9123456780"})
    assert client.get(f"/students/{sid}").json()["phone"] == "9123456780"


def test_patch_validates_result(client):
    sid = client.post("/students", json=make_student()).json()["id"]
    assert client.patch(f"/students/{sid}", json={"email": "bad"}).status_code == 422
    # Removing the only contact methods is not allowed.
    assert client.patch(f"/students/{sid}", json={"email": None, "phone": None}).status_code == 422
    # Nothing was changed by the failed attempts.
    assert client.get(f"/students/{sid}").json()["email"] == "test.student@example.com"


def test_patch_missing_404(client):
    assert client.patch("/students/42", json={"course": "X"}).status_code == 404


def test_patch_duplicate_email_409(client):
    client.post("/students", json=make_student(email="one@example.com"))
    two = client.post("/students", json=make_student(email="two@example.com")).json()
    assert client.patch(f"/students/{two['id']}", json={"email": "one@example.com"}).status_code == 409


# ---------- Delete ----------
def test_delete_student(client):
    sid = client.post("/students", json=make_student()).json()["id"]
    assert client.delete(f"/students/{sid}").status_code == 204
    assert client.get(f"/students/{sid}").status_code == 404
    assert client.get("/students").json() == []


def test_delete_missing_404(client):
    assert client.delete("/students/42").status_code == 404


# ---------- Persistence ----------
def test_data_persists_across_app_restarts(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("STUDENTS_DB", str(tmp_path / "persist.db"))
    with TestClient(app) as first:
        first.post("/students", json=make_student())
    with TestClient(app) as second:  # simulates restarting the server
        students = second.get("/students").json()
    assert len(students) == 1 and students[0]["name"] == "Test Student"
