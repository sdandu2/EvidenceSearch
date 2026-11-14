"""Verify a running EvidenceSearch API returns the *actual local SciFact corpus*.

Usage (after starting both servers):
  python -m backend.smoke_live --frontend http://localhost:3000

This test never downloads datasets/models and does not use relevance labels.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from backend.engine import read_corpus

QUERY = "Bone marrow cells don't contribute to adult macrophage compartments."
METHODS = ("bm25", "hybrid", "reranked")


def get_json(url: str, payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"} if body is not None else {},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Request failed: {url} ({exc}). Are the API and frontend running?") from exc


def audit(response: dict, corpus: dict) -> dict:
    """Check response semantics against source documents, never against fabricated examples."""
    if response.get("query") != QUERY:
        raise AssertionError("Returned query differs from submitted input")
    if response.get("collection", {}).get("document_count") != len(corpus):
        raise AssertionError("Unexpected indexed document count")
    methods = response.get("methods", {})
    if set(methods) != set(METHODS):
        raise AssertionError(f"Missing retrieval lists: {set(METHODS) - set(methods)}")
    inspected = 0
    for method in METHODS:
        ranked = methods[method]
        if len(ranked) != 10:
            raise AssertionError(f"Expected ten results for {method}, got {len(ranked)}")
        ids = [r["document_id"] for r in ranked]
        if len(set(ids)) != 10:
            raise AssertionError(f"Duplicate documents in {method} ranking")
        for rank, item in enumerate(ranked, start=1):
            original = corpus.get(item["document_id"])
            if original is None:
                raise AssertionError(f"Unknown corpus document: {item['document_id']}")
            if item["title"] != original["title"] or item["abstract"] != original["text"]:
                raise AssertionError(f"Source text differs: {item['document_id']}")
            if item["rank"] != rank or item["method"] != method:
                raise AssertionError("Incorrect rank or method metadata")
            inspected += 1
    traces = response.get("traces", [])
    if not traces:
        raise AssertionError("Rank tracking is empty")
    for trace in traces:
        if trace["document_id"] not in corpus or set(trace.get("ranks", {})) != set(METHODS):
            raise AssertionError("Invalid rank-tracking document")
    return {"status": "PASS", "method_counts": {k: len(methods[k]) for k in METHODS},
            "source_text_rows_checked": inspected, "traces_checked": len(traces),
            "elapsed_ms_reported": response.get("elapsed_ms"),
            "top_result": {"id": methods["reranked"][0]["document_id"],
                           "title": methods["reranked"][0]["title"]}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend", default="http://localhost:3000")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    corpus = read_corpus(root / "data" / "scifact" / "corpus.jsonl")
    if len(corpus) != 5183:
        raise RuntimeError(f"Expected 5183 SciFact documents; found {len(corpus)}")
    api_status = get_json(args.api.rstrip("/") + "/api/health")
    if api_status.get("status") != "ready" or api_status.get("documents") != len(corpus):
        raise AssertionError("Inference backend is not ready")
    benchmark = get_json(args.api.rstrip("/") + "/api/benchmarks")
    if benchmark.get("query_count") != 647:
        raise AssertionError("Benchmark endpoint did not load locked holdout")
    start = time.perf_counter()
    data = get_json(args.api.rstrip("/") + "/api/search", {"query": QUERY, "limit": 10})
    direct = audit(data, corpus)
    elapsed = round(1000*(time.perf_counter() - start), 2)
    # Check frontend Next.js proxy independently; it should point to same live API.
    frontend_health = get_json(args.frontend.rstrip("/") + "/api/status")
    if frontend_health.get("status") != "ready":
        raise AssertionError("Next.js proxy does not reach live FastAPI")
    proxied = get_json(args.frontend.rstrip("/") + "/api/search", {"query": QUERY})
    via_frontend = audit(proxied, corpus)
    if direct["top_result"] != via_frontend["top_result"]:
        raise AssertionError("Frontend and API disagree on top document")
    summary = {"status": "PASS", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
               "corpus_count": len(corpus), "query": QUERY, "direct": direct,
               "via_frontend": via_frontend, "direct_http_elapsed_ms": elapsed,
               "note": "Real local SciFact retrieval; not live internet indexing."}
    outfile = root / "reports" / "app" / "live_smoke.json"
    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("PASS: live API and Next.js proxy returned actual SciFact abstracts")
    print("Verified:", direct["source_text_rows_checked"], "source-text rows and", direct["traces_checked"], "ranking traces")
    print("Top reranked paper:", direct["top_result"]["title"])
    print("Report:", outfile)


if __name__ == "__main__":
    main()
