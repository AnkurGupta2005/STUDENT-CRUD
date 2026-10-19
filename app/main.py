"""FastAPI entry point.  Run with:  uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import init_db
from .routers import ai, students


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # creates the SQLite file and table on first run
    yield


app = FastAPI(
    title="Students Database API",
    description="CRUD API for student records (FastAPI + SQLite) with an optional "
                "local-LLM (Ollama) question-answering endpoint.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(students.router)
app.include_router(ai.router)


@app.get("/", tags=["health"], summary="Health check")
def root():
    return {"status": "ok", "docs": "/docs"}
