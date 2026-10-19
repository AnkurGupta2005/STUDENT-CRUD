"""Fill the database with DUMMY students for demos and for trying the AI endpoint.

Usage:  python seed.py
All names, emails and phone numbers below are made up (example.com addresses).
Existing students with the same email are skipped, so it is safe to run twice.
"""
from app import crud
from app.database import connect, init_db
from app.schemas import StudentCreate

DUMMY_STUDENTS = [
    ("Aarav Sharma", "2004-05-17", "aarav.sharma@example.com", "+91 90000 00001", "Computer Science", "Bhubaneswar", "2022-08-01"),
    ("Diya Patel", "2006-02-10", "diya.patel@example.com", "+91 90000 00002", "Mechanical Engineering", "Cuttack", "2024-08-05"),
    ("Rohan Das", "2001-11-30", "rohan.das@example.com", "+91 90000 00003", "Computer Science", "Puri", "2019-08-01"),
    ("Meera Nair", "2005-12-31", "meera.nair@example.com", "+91 90000 00004", "Physics", "Rourkela", "2023-08-07"),
    ("Kabir Singh", "2003-07-21", "kabir.singh@example.com", "+91 90000 00005", "Electrical Engineering", "Sambalpur", "2021-08-02"),
    ("Ananya Mishra", "2007-01-14", "ananya.mishra@example.com", "+91 90000 00006", "Computer Science", "Bhubaneswar", "2025-08-04"),
    ("Vikram Reddy", "2000-09-09", "vikram.reddy@example.com", None, "Mathematics", "Berhampur", "2018-08-01"),
    ("Sana Khan", "2006-06-25", None, "+91 90000 00008", "Physics", "Balasore", "2024-08-05"),
]


def main() -> None:
    init_db()
    conn = connect()
    added = 0
    try:
        for name, dob, email, phone, course, address, enrolled in DUMMY_STUDENTS:
            student = StudentCreate(name=name, date_of_birth=dob, email=email, phone=phone,
                                    course=course, address=address, enrollment_date=enrolled)
            try:
                crud.create_student(conn, student)
                added += 1
            except crud.DuplicateEmailError:
                pass
    finally:
        conn.close()
    print(f"Seeded {added} dummy student(s).")


if __name__ == "__main__":
    main()
