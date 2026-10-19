"""Pydantic models: request validation and response shapes."""
import re
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")
MIN_DOB = date(1900, 1, 1)


def _blank_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = value.strip()
    return value or None


class StudentCreate(BaseModel):
    """Full student record. Used for POST and PUT, and to validate PATCH."""

    name: str = Field(..., min_length=1, max_length=100, examples=["Aarav Sharma"])
    date_of_birth: date = Field(..., examples=["2004-05-17"])
    email: Optional[str] = Field(None, max_length=254, examples=["aarav@example.com"])
    phone: Optional[str] = Field(None, examples=["+91 98765 43210"])
    course: Optional[str] = Field(None, max_length=100, examples=["Computer Science"])
    address: Optional[str] = Field(None, max_length=300)
    enrollment_date: Optional[date] = Field(None, examples=["2023-08-01"])

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be blank")
        return v

    @field_validator("course", "address", mode="before")
    @classmethod
    def clean_optional_text(cls, v):
        return _blank_to_none(v) if isinstance(v, str) else v

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v):
        if not isinstance(v, str):
            return v
        v = _blank_to_none(v)
        if v is None:
            return None
        if not EMAIL_RE.match(v):
            raise ValueError("invalid email address")
        return v.lower()

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, v):
        if not isinstance(v, str):
            return v
        v = _blank_to_none(v)
        if v is None:
            return None
        if not PHONE_RE.match(v) or sum(c.isdigit() for c in v) < 7:
            raise ValueError("invalid phone number (need at least 7 digits)")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def check_dob(cls, v: date) -> date:
        if v < MIN_DOB or v >= date.today():
            raise ValueError("date_of_birth must be between 1900-01-01 and today")
        return v

    @field_validator("enrollment_date")
    @classmethod
    def check_enrollment_not_far_future(cls, v: Optional[date]) -> Optional[date]:
        # Allow a small amount of pre-registration, but not nonsense dates.
        if v is not None and v.year > date.today().year + 1:
            raise ValueError("enrollment_date is too far in the future")
        return v

    @model_validator(mode="after")
    def check_contact_and_dates(self):
        if not self.email and not self.phone:
            raise ValueError("provide at least one contact: email or phone")
        if self.enrollment_date and self.enrollment_date <= self.date_of_birth:
            raise ValueError("enrollment_date must be after date_of_birth")
        return self


class StudentUpdate(BaseModel):
    """Partial update (PATCH). Only the fields that are sent are changed.

    The merged record is re-validated with StudentCreate, so every rule above
    still applies to the final result.
    """

    name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None


class StudentOut(StudentCreate):
    id: int


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500,
                          examples=["How many students are there?"])


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    total_students: int
    matched_students: int
    filters_applied: list[str]
    records_used: list[StudentOut]
