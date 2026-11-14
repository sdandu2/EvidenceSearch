"""Check that the Observatory atlas is backed by local SciFact originals.

Run once the FastAPI server is up:
    python -m backend.smoke_observatory
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from backend.engine import read_corpus

QUERY = "TCR/CD3 microdomains are required to induce the immunologic synapse to activate T cells."


def audit(payload: dict, corpus: dict) -> dict:
    assert payload.get("collection", {}).get("name") == "SciFact"
    atlas = payload.get("atlas") or {}
    points = atlas.get("points") or []
    links = atlas.get("links") or []
    assert 3 <= len(points) <= 32, "Missing or oversized atlas"
    assert len(points) == len({p["document_id"] for p in points})
    assert atlas.get("layout") == "miniLM-query-relative-pca"
    for point in points:
        source = corpus[point["document_id"]]
        assert point["title"] == source["title"], "Atlas title differs from original corpus"
        assert point["abstract"] == source["text"], "Atlas abstract differs from original corpus"
        assert all(-0.95 <= float(point[k]) <= 0.95 for k in ("x", "y"))
        assert set(point["ranks"]) == {"bm25", "hybrid", "reranked"}
    atlas_ids = {p["document_id"] for p in points}
    for link in links:
        assert link["source"] in atlas_ids and link["target"] in atlas_ids
        assert -1 <= float(link["cosine"]) <= 1
    for method in ("bm25", "hybrid", "reranked"):
        results = payload["methods"][method]
        assert 1 <= len(results) <= 10
        for row in results:
            doc = corpus[row["document_id"]]
            assert row["title"] == doc["title"]
            assert row["abstract"] == doc["text"]
    return {
        "query": payload["query"],
        "atlas_documents_verified": len(points),
        "embedding_links_verified": len(links),
        "results_verified": sum(len(payload["methods"][m]) for m in ("bm25", "hybrid", "reranked")),
        "status": "PASS",
    }


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    corpus = read_corpus(root / "data" / "scifact" / "corpus.jsonl")
    base = os.environ.get("EVIDENCESEARCH_API_BASE", "http://127.0.0.1:8000").rstrip("/")
    body = json.dumps({"query": QUERY, "limit": 10}).encode()
    req = Request(base + "/api/search", data=body, headers={"content-type": "application/json"}, method="POST")
    with urlopen(req, timeout=90) as response:
        payload = json.load(response)
    outcome = audit(payload, corpus)
    dest = root / "reports" / "app" / "observatory_smoke.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(outcome, indent=2), encoding="utf-8")
    print(json.dumps(outcome, indent=2))
    print("Saved:", dest)


if __name__ == "__main__":
    main()
