"""POST /ai/ask  - optional Ollama-powered Q&A over the student records."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from .. import ai, crud
from ..database import get_db
from ..schemas import AskRequest, AskResponse

router = APIRouter(prefix="/ai", tags=["ai (optional)"])


@router.post("/ask", response_model=AskResponse, summary="Ask a question about the students")
def ask(body: AskRequest, db: sqlite3.Connection = Depends(get_db)):
    records, applied = ai.retrieve(db, body.question)
    total = crud.count_students(db)
    prompt = ai.build_prompt(body.question, records, total, applied)

    try:
        answer = ai.call_ollama(prompt)
    except ai.OllamaUnavailable as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))

    return AskResponse(
        question=body.question,
        answer=answer,
        model=ai.ollama_settings()[1],
        total_students=total,
        matched_students=len(records),
        filters_applied=applied,
        records_used=records[: ai.MAX_CONTEXT_RECORDS],
    )
