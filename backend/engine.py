"""Frozen SciFact retrieval pipeline, reconstructed from Notebooks 01–05.

No relevance labels are used for inference. No fabricated results, model-score
probabilities, or external search calls. Dataset and embedding identity are
verified against the existing notebook cache.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Protocol

import numpy as np

DENSE_MODEL = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
DENSE_REVISION = "b207367332321f8e44f96e224ef15bc607f4dbf0"
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L6-v2"
DATASET_SIZE = 5183
TOP_CANDIDATES = 100
RRF_K = 60
BM25_K1 = 1.5
BM25_B = 0.75
TOKENIZER = re.compile(r"[a-z0-9]+", flags=re.ASCII)


class Embedder(Protocol):
    def encode(self, texts: list[str], **kwargs: Any) -> Any: ...


class Reranker(Protocol):
    def predict(self, pairs: list[tuple[str, str]], **kwargs: Any) -> Any: ...


def tokenize(s: str) -> list[str]:
    return TOKENIZER.findall(s.lower())


def read_corpus(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"SciFact corpus missing: {path}. Run Notebook 01 first.")
    result: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            doc_id = str(row["_id"])
            if doc_id in result:
                raise ValueError(f"Duplicate SciFact document ID: {doc_id}")
            result[doc_id] = {"title": str(row.get("title") or ""), "text": str(row.get("text") or "")}
    return result


def verified_embeddings(root: Path, doc_ids: list[str], *, expected_rows: int = DATASET_SIZE) -> np.ndarray:
    """Reject changed datasets, reordered documents, or a different encoder revision."""
    folder = root / "data" / "scifact"
    path = root / "artifacts" / "embeddings" / "scifact_multiqa_minilm_l6_cos_v1_seed31.npz"
    if not path.is_file():
        raise FileNotFoundError(f"Frozen document embeddings missing: {path}. Run Notebook 02 first.")
    source_corpus = folder / "corpus.jsonl"
    source_queries = folder / "queries.jsonl"
    if not source_queries.is_file():
        raise FileNotFoundError(f"SciFact queries missing: {source_queries}")
    signature = hashlib.sha256(json.dumps({
        "model": DENSE_MODEL, "revision": DENSE_REVISION,
        "corpus_sha256": hashlib.sha256(source_corpus.read_bytes()).hexdigest(),
        "queries_sha256": hashlib.sha256(source_queries.read_bytes()).hexdigest(),
        "text_policy": "title_space_abstract", "normalization": "l2",
    }, sort_keys=True).encode()).hexdigest()
    with np.load(path, allow_pickle=False) as data:
        meta = json.loads(str(data["metadata"].item()))
        if meta.get("signature") != signature or meta.get("model") != DENSE_MODEL or meta.get("revision") != DENSE_REVISION:
            raise ValueError("Document embedding cache does not match the frozen SciFact dataset/model configuration")
        if list(data["document_ids"].astype(str)) != doc_ids:
            raise ValueError("Document embedding IDs/order do not match the SciFact corpus")
        embeddings = np.asarray(data["document_embeddings"], dtype=np.float32)
    if embeddings.shape != (expected_rows, 384) or not np.isfinite(embeddings).all():
        raise ValueError(f"Unexpected document embedding shape or values: {embeddings.shape}")
    if not np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, atol=0.002):
        raise ValueError("Cached document embeddings are not L2 normalized")
    return np.ascontiguousarray(embeddings)


def fuse_rrf(first: list[str], second: list[str], k: int = RRF_K, limit: int = TOP_CANDIDATES) -> list[tuple[str, float]]:
    if k <= 0 or len(first) != len(set(first)) or len(second) != len(set(second)):
        raise ValueError("Invalid inputs to reciprocal rank fusion")
    scores: dict[str, float] = defaultdict(float)
    for ranking in (first, second):
        for rank, doc_id in enumerate(ranking, 1):
            scores[doc_id] += 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]


class RetrievalEngine:
    def __init__(self, corpus: dict[str, dict[str, str]], embeddings: np.ndarray,
                 embedder: Embedder, reranker: Reranker) -> None:
        if not corpus:
            raise ValueError("A nonempty corpus is required")
        self.corpus = corpus
        self.doc_ids = sorted(corpus)
        self.doc_texts = [f"{corpus[d]['title']} {corpus[d]['text']}".strip() for d in self.doc_ids]
        self.text_lookup = dict(zip(self.doc_ids, self.doc_texts))
        self.embeddings = np.asarray(embeddings, dtype=np.float32)
        if self.embeddings.shape != (len(self.doc_ids), 384):
            raise ValueError("Embedding row count/dimension mismatch")
        self.embedder = embedder
        self.reranker = reranker
        self._model_lock = threading.Lock()  # bounded inference on small CPU hosts
        self.doc_lengths = np.zeros(len(self.doc_ids), dtype=np.float64)
        raw_postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, doc_text in enumerate(self.doc_texts):
            counts = Counter(tokenize(doc_text))
            self.doc_lengths[i] = sum(counts.values())
            for term, tf in counts.items():
                raw_postings[term].append((i, tf))
        self.avg_len = float(self.doc_lengths.mean())
        self.postings: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self.idf: dict[str, float] = {}
        for term, entries in raw_postings.items():
            ids = np.array([p[0] for p in entries], dtype=np.int32)
            tf = np.array([p[1] for p in entries], dtype=np.float64)
            self.postings[term] = (ids, tf)
            df = len(entries)
            self.idf[term] = math.log1p((len(self.doc_ids) - df + 0.5) / (df + 0.5))

    def bm25(self, query: str, limit: int = TOP_CANDIDATES) -> list[tuple[str, float]]:
        scores = np.zeros(len(self.doc_ids), dtype=np.float64)
        for term in set(tokenize(query)):
            if term not in self.postings:
                continue
            idx, tf = self.postings[term]
            norm = 1 - BM25_B + BM25_B * self.doc_lengths[idx] / self.avg_len
            scores[idx] += self.idf[term] * tf * (BM25_K1 + 1) / (tf + BM25_K1 * norm)
        n = min(limit, len(scores))
        threshold = np.partition(scores, len(scores) - n)[len(scores) - n]
        eligible = np.flatnonzero(scores >= threshold)
        ordered = sorted(eligible, key=lambda i: (-float(scores[i]), self.doc_ids[int(i)]))[:n]
        return [(self.doc_ids[int(i)], float(scores[i])) for i in ordered]

    def dense(self, query_embedding: np.ndarray, limit: int = TOP_CANDIDATES) -> list[tuple[str, float]]:
        similarities = self.embeddings @ query_embedding
        indexes = np.argsort(-similarities, kind="stable")[:limit]
        return [(self.doc_ids[int(i)], float(similarities[i])) for i in indexes]

    def _result(self, doc_id: str, rank: int, score: float, method: str) -> dict[str, Any]:
        record = self.corpus[doc_id]
        return {
            "document_id": doc_id, "rank": rank, "score": round(float(score), 7),
            "title": record["title"], "abstract": record["text"], "method": method,
        }

    def _atlas(self, query_vector: np.ndarray, ranked: dict[str, list[tuple[str, float]]]) -> dict[str, Any]:
        """Small, query-relative 2D view of *actual* cached MiniLM embeddings.

        PCA is lossy. Connections are nearest neighbors by cosine similarity,
        never citations, scientific agreement, or ground-truth evidence links.
        """
        ids = list(dict.fromkeys(
            [d for d, _ in ranked["reranked"][:12]]
            + [d for d, _ in ranked["bm25"][:10]]
            + [d for d, _ in ranked["hybrid"][:12]]
        ))[:32]
        if not ids:
            return {"points": [], "links": [], "layout": "miniLM-query-relative-pca"}
        idx_by_id = {doc_id: index for index, doc_id in enumerate(self.doc_ids)}
        vectors = self.embeddings[[idx_by_id[doc_id] for doc_id in ids]].astype(np.float64)
        query_vec = np.asarray(query_vector, dtype=np.float64)
        differences = vectors - query_vec
        # Small sample kernel PCA; only up to 32 x 32 matrix is eigendecomposed.
        gram = differences @ differences.T
        values, basis = np.linalg.eigh(gram)
        axes = basis[:, -2:] * np.sqrt(np.maximum(values[-2:], 0))[None, :]
        if axes.shape[1] == 1:
            axes = np.column_stack([axes, np.zeros(len(ids))])
        # Stable eigenvector orientation across identical inputs.
        for col in range(2):
            pivot = int(np.argmax(np.abs(axes[:, col])))
            if axes[pivot, col] < 0:
                axes[:, col] *= -1
        radius = np.linalg.norm(axes, axis=1)
        scale = max(float(np.percentile(radius, 90)), 1e-6)
        coords = np.clip(axes / scale * 0.83, -0.94, 0.94)
        ranks = {name: {doc_id: i for i, (doc_id, _) in enumerate(items, 1)}
                 for name, items in ranked.items()}
        similarities = vectors @ query_vec
        points = [{
            "document_id": doc_id,
            "title": self.corpus[doc_id]["title"],
            "abstract": self.corpus[doc_id]["text"],
            "x": round(float(coords[i, 0]), 5), "y": round(float(coords[i, 1]), 5),
            "query_cosine": round(float(similarities[i]), 5),
            "ranks": {name: ranks[name].get(doc_id) for name in ranked},
        } for i, doc_id in enumerate(ids)]
        sim = vectors @ vectors.T
        links = []
        seen = set()
        for i in range(len(ids)):
            # Two nearest document-embedding neighbors, with a conservative threshold.
            neighbors = np.argsort(-sim[i], kind="stable")
            for j in neighbors:
                if i == j or sim[i, j] < 0.62:
                    continue
                edge = (min(i, int(j)), max(i, int(j)))
                if edge in seen:
                    continue
                seen.add(edge)
                links.append({"source": ids[edge[0]], "target": ids[edge[1]],
                              "cosine": round(float(sim[i, j]), 5)})
                if sum(i in edge_pair for edge_pair in seen) >= 2:
                    break
        return {"points": points, "links": links,
                "layout": "miniLM-query-relative-pca",
                "note": "2D coordinates approximate cached MiniLM embedding geometry relative to the query; projection is lossy. Links reflect embedding cosine similarity, not citations or scientific agreement."}

    def search(self, query: str, limit: int = 10) -> dict[str, Any]:
        start = time.perf_counter()
        # One pipeline run produces synchronized ranked lists for the same input.
        with self._model_lock:
            bm = self.bm25(query)
            emb = np.asarray(self.embedder.encode([query], normalize_embeddings=True,
                        convert_to_numpy=True, show_progress_bar=False), dtype=np.float32).reshape(-1)
            if emb.shape != (384,) or not np.isfinite(emb).all():
                raise ValueError("Invalid query embedding")
            dn = self.dense(emb)
            fusion = fuse_rrf([d for d, _ in bm], [d for d, _ in dn])
            fused_ids = [d for d, _ in fusion]
            pairs = [(query, self.text_lookup[d]) for d in fused_ids]
            scores = np.asarray(self.reranker.predict(pairs, batch_size=8,
                        show_progress_bar=False, convert_to_numpy=True), dtype=np.float32).reshape(-1)
            if len(scores) != len(fused_ids) or not np.isfinite(scores).all():
                raise ValueError("Invalid reranker output")
            # stable sorting preserves the RRF order on equal cross-encoder scores
            order = np.argsort(-scores, kind="stable")
            reranked = [(fused_ids[int(i)], float(scores[int(i)])) for i in order]

        ranked = {"bm25": bm, "hybrid": fusion, "reranked": reranked}
        methods = {
            name: [self._result(doc, rank, score, name)
                   for rank, (doc, score) in enumerate(items[:limit], 1)]
            for name, items in ranked.items()
        }
        # Include union of first five across methods, ranked by final method first.
        trace_ids = list(dict.fromkeys(
            [d for d, _ in reranked[:5]] + [d for d, _ in bm[:5]] + [d for d, _ in fusion[:5]]
        ))
        rank_maps = {name: {doc: rank for rank, (doc, _) in enumerate(rows, 1)}
                     for name, rows in ranked.items()}
        traces = [{"document_id": d, "title": self.corpus[d]["title"],
                   "ranks": {name: rank_maps[name].get(d) for name in ranked}}
                  for d in trace_ids]
        atlas = self._atlas(emb, ranked)
        return {
            "atlas": atlas,
            "query": query, "collection": {"id": "scifact", "name": "SciFact", "document_count": len(self.doc_ids)},
            "methods": methods, "traces": traces, "candidate_count": len(fusion),
            "elapsed_ms": round((time.perf_counter() - start) * 1000, 2),
            "score_note": "Scores are method-specific ranking outputs, not confidence or truth probabilities.",
        }


def verify_frozen_selection(root: Path) -> None:
    """Block accidental changes to the model-selection contract from Notebook 05."""
    path = root / "reports" / "experiments" / "scifact_locked_holdout_seed31" / "selection_lock.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Notebook 05 selection lock: {path}")
    selection = json.loads(path.read_text(encoding="utf-8"))
    frozen = selection.get("fixed_retrieval", {})
    reranker = selection.get("reranker", {})
    expected = {
        "bm25_k1": BM25_K1, "bm25_b": BM25_B,
        "dense_model": DENSE_MODEL, "dense_revision": DENSE_REVISION,
        "rrf_k": RRF_K, "bm25_candidate_count": TOP_CANDIDATES,
        "dense_candidate_count": TOP_CANDIDATES,
        "fused_candidate_count": TOP_CANDIDATES,
    }
    if selection.get("selected_model") != "CE · RRF@100":
        raise ValueError("Notebook 05 selected architecture does not match production code")
    for key, expected_value in expected.items():
        if frozen.get(key) != expected_value:
            raise ValueError(f"Frozen setting mismatch: {key}")
    if reranker.get("model") != CROSS_ENCODER_MODEL or reranker.get("max_length") != 256:
        raise ValueError("Frozen cross-encoder configuration differs")


def load_engine(root: Path) -> RetrievalEngine:
    """Load verified data and pretrained models once per backend process."""
    verify_frozen_selection(root)
    corpus = read_corpus(root / "data" / "scifact" / "corpus.jsonl")
    if len(corpus) != DATASET_SIZE:
        raise ValueError(f"Expected {DATASET_SIZE} SciFact documents; found {len(corpus)}")
    doc_ids = sorted(corpus)
    embeddings = verified_embeddings(root, doc_ids)
    # Preserve TLS verification; Windows users have OS CA stores configured via truststore.
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "45")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "180")
    from sentence_transformers import CrossEncoder, SentenceTransformer
    embedder = SentenceTransformer(DENSE_MODEL, revision=DENSE_REVISION, device="cpu", trust_remote_code=False)
    reranker = CrossEncoder(CROSS_ENCODER_MODEL, max_length=256, device="cpu", trust_remote_code=False)
    return RetrievalEngine(corpus, embeddings, embedder, reranker)


def load_benchmarks(root: Path) -> dict[str, Any]:
    path = root / "reports" / "experiments" / "scifact_locked_holdout_seed31" / "summary.json"
    if not path.is_file():
        raise FileNotFoundError(f"Missing Notebook 05 benchmark results: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("holdout_query_count") != 647 or raw.get("new_official_test_queries_scored") != 0:
        raise ValueError("Notebook 05 summary is not the expected 647-query internal holdout")
    required = ("BM25", "Hybrid RRF", "CE · RRF@100")
    metric_names = ("nDCG@10", "Recall@10", "MRR@10")
    metrics = raw["metrics"]
    for model in required:
        for name in metric_names:
            value = metrics[model][name]
            if not isinstance(value, (float, int)) or not 0 <= value <= 1:
                raise ValueError(f"Invalid benchmark metric: {model} {name}")
    return {
        "evaluation": "Reserved SciFact training-query holdout (647 claims), not untouched official test",
        "query_count": 647,
        "metrics": {method: {k: metrics[method][k] for k in metric_names} for method in required},
        "paired_vs_bm25": raw.get("paired_vs_BM25", []),
        "latency": raw.get("warm_cpu_latency", {}),
        "caveat": "Relevance judgments are incomplete; unjudged does not mean irrelevant.",
    }
