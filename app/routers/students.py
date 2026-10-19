"""CRUD endpoints for /students."""
import json
import sqlite3
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import ValidationError

from .. import crud
from ..database import get_db
from ..schemas import StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/students", tags=["students"])

NOT_FOUND = "Student {id} not found"


def _duplicate_email(email: Optional[str]) -> HTTPException:
    return HTTPException(status.HTTP_409_CONFLICT, f"A student with email '{email}' already exists")


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED,
             summary="Create a student")
def create_student(student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        return crud.create_student(db, student)
    except crud.DuplicateEmailError:
        raise _duplicate_email(student.email)


@router.get("", response_model=list[StudentOut], summary="List / filter students")
def list_students(
    name: Optional[str] = Query(None, description="Case-insensitive substring of the name"),
    course: Optional[str] = Query(None, description="Case-insensitive substring of the course"),
    email: Optional[str] = Query(None, description="Exact email match"),
    born_after: Optional[date] = Query(None, description="Date of birth strictly after this date"),
    born_before: Optional[date] = Query(None, description="Date of birth strictly before this date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: sqlite3.Connection = Depends(get_db),
):
    return crud.list_students(
        db, name=name, course=course, email=email,
        born_after=born_after, born_before=born_before, skip=skip, limit=limit,
    )


@router.get("/{student_id}", response_model=StudentOut, summary="View a student")
def get_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    student = crud.get_student(db, student_id)
    if student is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND.format(id=student_id))
    return student


@router.put("/{student_id}", response_model=StudentOut, summary="Replace a student's details")
def replace_student(student_id: int, student: StudentCreate, db: sqlite3.Connection = Depends(get_db)):
    try:
        updated = crud.update_student(db, student_id, student)
    except crud.DuplicateEmailError:
        raise _duplicate_email(student.email)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND.format(id=student_id))
    return updated


@router.patch("/{student_id}", response_model=StudentOut, summary="Update some of a student's details")
def patch_student(student_id: int, changes: StudentUpdate, db: sqlite3.Connection = Depends(get_db)):
    current = crud.get_student(db, student_id)
    if current is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND.format(id=student_id))

    merged = {**current, **changes.model_dump(exclude_unset=True)}
    merged.pop("id", None)
    try:
        validated = StudentCreate(**merged)
    except ValidationError as exc:
        # Same 422 shape FastAPI uses for body errors.
        detail = json.loads(exc.json(include_url=False, include_context=False))
        raise HTTPException(422, detail)

    try:
        updated = crud.update_student(db, student_id, validated)
    except crud.DuplicateEmailError:
        raise _duplicate_email(validated.email)
    return updated


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a student")
def delete_student(student_id: int, db: sqlite3.Connection = Depends(get_db)):
    if not crud.delete_student(db, student_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, NOT_FOUND.format(id=student_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
