"""FastAPI router for local, private multi-domain research retrieval."""
from __future__ import annotations

import os
import threading
from pathlib import Path
import csv
import json
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from backend.expanded_engine import DOMAINS, ExpandedEngine, load_expanded_engine

router = APIRouter(prefix="/api/research", tags=["Expanded research (local only)"])
ROOT = Path(os.environ.get("EVIDENCESEARCH_ROOT", Path(__file__).resolve().parents[1])).resolve()
_engine: ExpandedEngine | None = None
_init_lock = threading.Lock()


def get_engine() -> ExpandedEngine:
    global _engine
    if _engine is None:
        with _init_lock:
            if _engine is None:
                _engine = load_expanded_engine(ROOT)
    return _engine


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=600)
    domain: str
    limit: int = Field(default=10, ge=1, le=20)
    year_min: int | None = Field(default=None, ge=1800, le=2100)
    year_max: int | None = Field(default=None, ge=1800, le=2100)

    @field_validator("query")
    @classmethod
    def clean_question(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3 or not any(ch.isalnum() for ch in cleaned):
            raise ValueError("Enter a meaningful research question")
        return cleaned

    @field_validator("domain")
    @classmethod
    def supported_field(cls, value: str) -> str:
        if value not in DOMAINS:
            raise ValueError("Select a supported research field")
        return value


@router.get("/status")
async def research_status():
    try:
        root = ROOT
        files = [root / "data/research/corpus_expanded_PRIVATE.jsonl",
                 root / "reports/experiments/research_corpus_expansion_seed31/expansion_manifest.json",
                 root / "data/research/model_cache/expanded_minilm_documents_seed31.npz"]
        return {"configured": all(p.is_file() for p in files), "model_loaded": _engine is not None,
                "domains": list(DOMAINS), "public_abstract_rights": "NOT_VERIFIED"}
    except Exception:
        return {"configured": False, "model_loaded": False}


@router.get("/domains")
async def research_domains():
    try:
        # Cheap metadata-only endpoint: never load transformer weights just to show the selector.
        path = ROOT / "reports/experiments/research_corpus_expansion_seed31/expansion_manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        questions = {d: [] for d in DOMAINS}
        guided = ROOT / "data/research/guided_questions_unjudged.csv"
        if guided.is_file():
            with guided.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    d, q = row.get("domain", ""), row.get("question", "").strip()
                    if d in questions and q and q not in questions[d]: questions[d].append(q)
        summaries = {str(r["domain"]): r for r in manifest.get("domain_summary", [])}
        fields = [{"name": d, "documents": int(summaries[d]["expanded_memberships"]),
                   "suggested_questions": questions[d][:8]} for d in DOMAINS]
        return {"corpus": "Expanded research collection", "fields": fields,
                "model_loaded": _engine is not None, "public_abstract_rights": "NOT_VERIFIED",
                "service": "local_only"}
    except (FileNotFoundError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(status_code=503, detail="Expanded search assets are incomplete or inconsistent; rerun Notebook 13.") from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Expanded search could not initialize; inspect backend logs.") from exc


@router.post("/search")
async def research_search(body: ResearchRequest):
    if body.year_min and body.year_max and body.year_min > body.year_max:
        raise HTTPException(status_code=422, detail="year_min must not exceed year_max")
    try:
        return await run_in_threadpool(lambda: get_engine().search(query=body.query, domain=body.domain,
            limit=body.limit, year_min=body.year_min, year_max=body.year_max))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Expanded search unavailable. Check backend logs and local artifacts.") from exc
