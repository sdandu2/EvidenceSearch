"""FastAPI endpoints and model lifecycle. Run from project root:
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from backend.engine import RetrievalEngine, load_benchmarks, load_engine
from backend.research_api import router as research_router

ROOT = Path(os.environ.get("EVIDENCESEARCH_ROOT", Path(__file__).resolve().parents[1])).resolve()


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=600)
    limit: int = Field(default=10, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 3 or not any(ch.isalnum() for ch in v):
            raise ValueError("Enter a meaningful scientific query")
        return v


def create_app(engine_factory: Callable[[Path], RetrievalEngine] = load_engine,
               benchmarks_factory: Callable[[Path], dict] = load_benchmarks,
               root: Path = ROOT) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.benchmarks = benchmarks_factory(root)
        app.state.engine = engine_factory(root)
        yield
        app.state.engine = None

    application = FastAPI(title="EvidenceSearch API", version="0.1.0", lifespan=lifespan,
                          description="SciFact scientific evidence ranking, not scientific fact verification")

    @application.get("/api/health")
    async def health(request: Request):
        return {"status": "ready", "collection": "SciFact", "documents": len(request.app.state.engine.doc_ids)}

    @application.get("/api/benchmarks")
    async def benchmarks(request: Request):
        return request.app.state.benchmarks

    @application.post("/api/search")
    async def search(payload: SearchRequest, request: Request):
        try:
            return await run_in_threadpool(request.app.state.engine.search, payload.query, payload.limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            # Avoid exposing internal file paths or stack traces to HTTP clients.
            raise HTTPException(status_code=500, detail="Inference failed. Check backend logs.") from exc
    application.include_router(research_router)
    return application


app = create_app()
