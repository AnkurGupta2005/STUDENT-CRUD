"""Optional bonus: answer natural-language questions with a local Ollama model.

Safety design
-------------
* The model NEVER touches the database and never writes SQL.
* The backend decides what to fetch. It looks for a small set of whitelisted
  patterns in the question (a birth-year range, a known course, a student's
  name) and runs ordinary parameterised queries through crud.list_students().
* The fetched records, plus exact counts computed in Python, are put into the
  prompt, and the model is told to answer only from them.
* Even a prompt-injection attempt in the question can only change the wording
  of the answer, because the model has no tools and no data access beyond the
  records we chose to show it.
"""
import os
import re
import sqlite3
from datetime import date

import httpx

from . import crud

MAX_CONTEXT_RECORDS = 50

SYSTEM_PROMPT = (
    "You are an assistant for a student records database. "
    "Answer the question using ONLY the data provided below. "
    "Use the exact counts given; do not count the records yourself. "
    "If the data does not contain the answer, say you could not find it. "
    "Do not invent students or details. Keep the answer short and clear."
)


class OllamaUnavailable(Exception):
    """Ollama is not running, or the model is not installed."""


def ollama_settings() -> tuple[str, str]:
    return (
        os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/"),
        os.getenv("OLLAMA_MODEL", "llama3.2:1b"),
    )


# --------------------------------------------------------------------------
# 1. Retrieval: decide which records are relevant (plain Python, no LLM)
# --------------------------------------------------------------------------
def retrieve(conn: sqlite3.Connection, question: str) -> tuple[list[dict], list[str]]:
    """Return (matching records, human-readable list of filters applied)."""
    q = question.lower()
    filters: dict = {}
    applied: list[str] = []

    # Birth-year ranges: "born after 2005", "born before 2000", "born in 2004",
    # "born between 2001 and 2004".
    if m := re.search(r"born\s+between\s+(\d{4})\s+(?:and|to|-)\s+(\d{4})", q):
        lo, hi = sorted((int(m.group(1)), int(m.group(2))))
        filters["born_after"], filters["born_before"] = date(lo - 1, 12, 31), date(hi + 1, 1, 1)
        applied.append(f"born between {lo} and {hi}")
    elif m := re.search(r"born\s+(?:after|since)\s+(\d{4})", q):
        y = int(m.group(1))
        filters["born_after"] = date(y, 12, 31)
        applied.append(f"born after {y}")
    elif m := re.search(r"born\s+before\s+(\d{4})", q):
        y = int(m.group(1))
        filters["born_before"] = date(y, 1, 1)
        applied.append(f"born before {y}")
    elif m := re.search(r"born\s+in\s+(\d{4})", q):
        y = int(m.group(1))
        filters["born_after"], filters["born_before"] = date(y - 1, 12, 31), date(y + 1, 1, 1)
        applied.append(f"born in {y}")

    everyone = crud.list_students(conn, limit=500)

    # Course mentioned in the question (matched against courses that really exist).
    courses = sorted({s["course"] for s in everyone if s["course"]}, key=len, reverse=True)
    for course in courses:
        if course.lower() in q:
            filters["course"] = course
            applied.append(f"course = {course}")
            break

    # A student mentioned by full name, or by first name as a whole word.
    named = [
        s for s in everyone
        if s["name"].lower() in q
        or re.search(rf"\b{re.escape(s['name'].split()[0].lower())}\b", q)
    ]
    if named and len(named) < len(everyone):
        applied.append("name mentioned: " + ", ".join(s["name"] for s in named))

    records = crud.list_students(conn, limit=500, **filters) if filters else everyone
    if named and len(named) < len(everyone):
        ids = {s["id"] for s in named}
        records = [r for r in records if r["id"] in ids]

    return records, applied


# --------------------------------------------------------------------------
# 2. Prompt + model call
# --------------------------------------------------------------------------
def build_prompt(question: str, records: list[dict], total: int, applied: list[str]) -> str:
    shown = records[:MAX_CONTEXT_RECORDS]
    lines = [
        f"- id={r['id']}; name={r['name']}; date_of_birth={r['date_of_birth']}; "
        f"course={r['course'] or 'n/a'}; enrollment_date={r['enrollment_date'] or 'n/a'}; "
        f"email={r['email'] or 'n/a'}; phone={r['phone'] or 'n/a'}"
        for r in shown
    ]
    note = ""
    if len(records) > len(shown):
        note = f"\n(Only the first {len(shown)} of {len(records)} matching records are listed.)"
    return (
        f"Total students in database: {total}\n"
        f"Filters applied: {', '.join(applied) if applied else 'none (all students)'}\n"
        f"Number of students matching the filters: {len(records)}\n"
        f"Matching records:\n{chr(10).join(lines) if lines else '(none)'}{note}\n\n"
        f"Question: {question}"
    )


def call_ollama(prompt: str) -> str:
    """Send the prompt to a local Ollama server and return the reply text."""
    base_url, model = ollama_settings()
    payload = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        # Generous timeout: the first request has to load the model into memory.
        resp = httpx.post(f"{base_url}/api/chat", json=payload, timeout=180)
        resp.raise_for_status()
    except httpx.ConnectError as exc:
        raise OllamaUnavailable(
            f"Cannot reach Ollama at {base_url}. Start it with `ollama serve`."
        ) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise OllamaUnavailable(
                f"Model '{model}' is not installed. Run `ollama pull {model}`."
            ) from exc
        raise OllamaUnavailable(f"Ollama returned an error: {exc.response.status_code}") from exc
    except httpx.TimeoutException as exc:
        raise OllamaUnavailable("Ollama took too long to respond.") from exc

    return resp.json()["message"]["content"].strip()
