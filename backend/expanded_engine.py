"""Local-only five-domain search over the frozen Notebook 12/13 artifacts.

No network requests at search time. This API deliberately does not assert research
truth, independent retrieval accuracy, or public redistribution permission.
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
from typing import Any

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import TfidfTransformer, TfidfVectorizer

DOMAINS = ("Neuroscience", "Climate Science", "Quantum Computing", "Genetics", "Immunology")
METHODS = ("bm25", "tfidf", "dense", "hybrid", "reranked")
MODEL_ID = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
MODEL_REVISION = "b207367332321f8e44f96e224ef15bc607f4dbf0"
CE_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
CANDIDATE_DEPTH = 100
RRF_K = 60
TOKEN_RE = re.compile(r"[a-z0-9]+(?:['-][a-z0-9]+)?")


def checksum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def signature(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     default=str).encode("utf-8")).hexdigest()


def membership(value: Any) -> set[str]:
    if isinstance(value, (list, tuple, set)):
        return {str(x).strip() for x in value if str(x).strip()}
    return {s.strip() for s in str(value or "").split("|") if s.strip()}


def text_of(p: dict) -> str:
    return str(p.get("title") or "").strip() + " " + str(p.get("abstract") or "").strip()


def stable_top(ids: list[str], scores: np.ndarray, depth: int) -> list[tuple[str, float]]:
    if len(ids) != len(scores) or not np.isfinite(scores).all():
        raise ValueError("Invalid ranking scores")
    order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))[:depth]
    return [(ids[i], float(scores[i])) for i in order]


def rrf(left: list[str], right: list[str], depth: int = CANDIDATE_DEPTH) -> list[tuple[str, float]]:
    weights = defaultdict(float)
    for ranking in (left, right):
        if len(ranking) != len(set(ranking)):
            raise ValueError("Duplicate RRF candidate")
        for rank, paper_id in enumerate(ranking, 1):
            weights[paper_id] += 1.0 / (RRF_K + rank)
    return sorted(weights.items(), key=lambda item: (-item[1], item[0]))[:depth]


class FieldIndex:
    """Restore Notebook 13's private, portable lexical snapshots; never unpickle."""
    def __init__(self, root: Path, domain: str, corpus_sha: str, paper_ids: list[str]):
        folder = root / "data" / "research" / "index_cache" / domain.lower().replace(" ", "_")
        expected_sig = signature({
            "corpus_sha256": corpus_sha, "domain": domain, "ids": paper_ids,
            "bm25": {"k1": 1.5, "b": 0.75},
            "tfidf": {"ngram_range": [1, 2], "stop_words": "english", "sublinear_tf": True},
        })
        metadata = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if metadata.get("signature") != expected_sig or metadata.get("doc_ids") != paper_ids:
            raise ValueError(f"Notebook 13 index identity mismatch for {domain}")
        self.paper_ids = paper_ids
        self.counts = sparse.load_npz(folder / "bm25_tf_counts.npz").tocsr()
        self.matrix = sparse.load_npz(folder / "tfidf_matrix.npz").tocsr()
        self.lengths = np.load(folder / "bm25_lengths.npy", allow_pickle=False).astype(np.float64)
        lexicon = json.loads((folder / "bm25_lexicon.json").read_text(encoding="utf-8"))
        self.terms = lexicon["terms"]
        self.term_index = {term: i for i, term in enumerate(self.terms)}
        self.idf = np.asarray(lexicon["idf"], dtype=np.float64)
        self.avg_len = float(lexicon["avgdl"])
        vector_meta = json.loads((folder / "tfidf_vectorizer.json").read_text(encoding="utf-8"))
        vocab = vector_meta["vocabulary"]
        vector_idf = np.asarray(vector_meta["idf"], dtype=np.float64)
        if (self.counts.shape != (len(paper_ids), len(self.terms))
                or self.matrix.shape != (len(paper_ids), len(vocab))
                or self.lengths.shape != (len(paper_ids),)
                or len(self.idf) != len(self.terms)
                or not np.isfinite(self.idf).all()
                or not np.isfinite(vector_idf).all()):
            raise ValueError(f"Invalid private lexical index shape for {domain}")
        self.vectorizer = TfidfVectorizer(vocabulary=vocab, ngram_range=(1, 2),
                                         stop_words="english", sublinear_tf=True, dtype=np.float32)
        self.vectorizer.vocabulary_ = vocab
        self.vectorizer.fixed_vocabulary_ = True
        self.vectorizer._tfidf = TfidfTransformer(norm="l2", use_idf=True, sublinear_tf=True)
        self.vectorizer._tfidf.idf_ = vector_idf

    def bm25(self, query: str) -> np.ndarray:
        result = np.zeros(len(self.paper_ids), dtype=np.float64)
        norm = 1.5 * (0.25 + 0.75 * self.lengths / max(self.avg_len, 1.0))
        for term in set(TOKEN_RE.findall(query.lower())):
            col = self.term_index.get(term)
            if col is None:
                continue
            vec = self.counts.getcol(col).tocoo()
            tf = vec.data.astype(np.float64)
            result[vec.row] += self.idf[col] * (tf * 2.5) / (tf + norm[vec.row] + 1e-12)
        return result

    def tfidf(self, query: str) -> np.ndarray:
        return (self.matrix @ self.vectorizer.transform([query]).T).toarray().reshape(-1).astype(np.float64)


class ExpandedEngine:
    def __init__(self, root: Path, *, encoder: Any, cross_encoder: Any,
                 min_documents: int = 5000):
        self.root = Path(root)
        path = self.root / "data" / "research" / "corpus_expanded_PRIVATE.jsonl"
        self.corpus_sha = checksum(path)
        manifest = json.loads((self.root / "reports" / "experiments" /
                               "research_corpus_expansion_seed31" /
                               "expansion_manifest.json").read_text(encoding="utf-8"))
        if manifest.get("expanded_sha256") != self.corpus_sha:
            raise ValueError("Corpus differs from frozen Notebook 12 snapshot")
        with path.open(encoding="utf-8") as stream:
            papers = [json.loads(row) for row in stream if row.strip()]
        self.papers = sorted(papers, key=lambda row: str(row.get("paper_id", "")))
        self.ids = [str(p.get("paper_id", "")) for p in self.papers]
        if (len(self.ids) < min_documents or len(self.ids) != len(set(self.ids))
                or not all(self.ids) or len(self.ids) != manifest.get("expanded_global_unique")):
            raise ValueError("Corpus IDs/count differ from frozen acquisition manifest")
        self.by_id = dict(zip(self.ids, self.papers))
        self.global_position = {pid: i for i, pid in enumerate(self.ids)}
        self.field_ids = {d: [pid for pid, p in zip(self.ids, self.papers)
                              if d in membership(p.get("domains"))] for d in DOMAINS}
        if any(not ids for ids in self.field_ids.values()):
            raise ValueError("Empty scientific field")
        self.fields = {d: FieldIndex(self.root, d, self.corpus_sha, ids)
                       for d, ids in self.field_ids.items()}
        doc_sig = signature({"sha": self.corpus_sha, "ids": self.ids,
                             "model": MODEL_ID, "revision": MODEL_REVISION,
                             "text_policy": "title_space_abstract", "norm": True,
                             "dtype": "float32"})
        emb_path = self.root / "data" / "research" / "model_cache" / "expanded_minilm_documents_seed31.npz"
        with np.load(emb_path, allow_pickle=False) as z:
            metadata = json.loads(str(z["metadata"].item()))
            embeddings = np.asarray(z["embeddings"], dtype=np.float32)
        if (metadata.get("signature") != doc_sig or embeddings.shape != (len(self.ids), 384)
                or not np.isfinite(embeddings).all()
                or not np.allclose(np.linalg.norm(embeddings, axis=1), 1, atol=0.01)):
            raise ValueError("Document embeddings do not match Notebook 13 configuration")
        self.embeddings = embeddings
        self.encoder = encoder
        self.cross_encoder = cross_encoder
        self.lock = threading.Lock()
        self.field_positions = {d: np.asarray([self.global_position[pid]
                                              for pid in ids], dtype=np.int32)
                                for d, ids in self.field_ids.items()}
        self.question_bank = self._read_questions()

    def _read_questions(self) -> dict[str, list[str]]:
        import csv
        path = self.root / "data" / "research" / "guided_questions_unjudged.csv"
        result = {d: [] for d in DOMAINS}
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as stream:
                for row in csv.DictReader(stream):
                    if row.get("domain") in DOMAINS and row.get("question", "").strip():
                        if row["question"] not in result[row["domain"]]:
                            result[row["domain"]].append(row["question"])
        return result

    def domains(self) -> dict:
        return {"corpus": "Expanded research collection", "snapshot_sha256": self.corpus_sha,
                "fields": [{"name": d, "documents": len(ids),
                            "suggested_questions": self.question_bank[d][:8]}
                           for d, ids in self.field_ids.items()],
                "public_abstract_rights": "NOT_VERIFIED", "service": "local_only"}

    @staticmethod
    def _publication_year(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def search(self, *, query: str, domain: str, limit: int = 10,
               year_min: int | None = None, year_max: int | None = None) -> dict:
        if domain not in self.fields:
            raise ValueError("Unknown research field")
        if len(query.strip()) < 3 or not any(c.isalnum() for c in query):
            raise ValueError("Enter a meaningful research question")
        start = time.perf_counter()
        with self.lock:
            field = self.fields[domain]
            indices = [i for i, pid in enumerate(field.paper_ids)
                       if (year_min is None or self._publication_year(self.by_id[pid].get("year")) >= year_min)
                       and (year_max is None or self._publication_year(self.by_id[pid].get("year")) <= year_max)]
            if not indices:
                return {"query": query, "domain": domain, "filtered_count": 0,
                        "methods": {m: [] for m in METHODS}, "elapsed_ms": 0,
                        "public_abstract_rights": "NOT_VERIFIED"}
            selected_ids = [field.paper_ids[i] for i in indices]
            depth = min(CANDIDATE_DEPTH, len(selected_ids))
            bm25 = stable_top(selected_ids, field.bm25(query)[indices], depth)
            tfidf = stable_top(selected_ids, field.tfidf(query)[indices], depth)
            query_vector = np.asarray(self.encoder.encode([query], normalize_embeddings=True,
                    convert_to_numpy=True, show_progress_bar=False), dtype=np.float32).reshape(-1)
            if query_vector.shape != (384,) or not np.isfinite(query_vector).all():
                raise ValueError("Invalid MiniLM query embedding")
            positions = self.field_positions[domain][indices]
            dense = stable_top(selected_ids, self.embeddings[positions] @ query_vector, depth)
            fused = rrf([i for i, _ in bm25], [i for i, _ in dense], depth)
            pairs = [(query, text_of(self.by_id[pid])) for pid, _ in fused]
            scores = np.asarray(self.cross_encoder.predict(pairs, batch_size=8,
                show_progress_bar=False, convert_to_numpy=True), dtype=np.float32).reshape(-1)
            if len(scores) != len(fused) or not np.isfinite(scores).all():
                raise ValueError("Invalid cross-encoder scores")
            reranked = stable_top([pid for pid, _ in fused], scores, depth)
        raw = {"bm25": bm25, "tfidf": tfidf, "dense": dense,
               "hybrid": fused, "reranked": reranked}
        def record(method: str, rank: int, item: tuple[str, float]) -> dict:
            pid, score = item
            p = self.by_id[pid]
            # local-only: rights for displaying these source abstracts are not verified.
            return {"paper_id": pid, "rank": rank, "score": round(score, 7),
                    "title": p.get("title", ""), "abstract": p.get("abstract", ""),
                    "year": p.get("year"), "authors": p.get("authors", ""),
                    "venue": p.get("venue", ""), "doi": p.get("doi", ""),
                    "source_url": p.get("url", ""), "method": method}
        return {"query": query, "domain": domain, "filtered_count": len(selected_ids),
                "methods": {m: [record(m, i, row) for i, row in enumerate(rows[:limit], 1)]
                            for m, rows in raw.items()},
                "elapsed_ms": round((time.perf_counter()-start)*1000, 1),
                "source": "Notebook 12 frozen expanded corpus",
                "evaluation": "Expanded-corpus retrieval relevance not independently verified",
                "public_abstract_rights": "NOT_VERIFIED",
                "score_note": "Ranking scores are not scientific truth probabilities."}


def load_expanded_engine(root: Path) -> ExpandedEngine:
    try:
        import truststore
        truststore.inject_into_ssl()
    except ImportError:
        pass
    import torch
    from sentence_transformers import SentenceTransformer, CrossEncoder
    device = os.getenv("EVIDENCESEARCH_RESEARCH_DEVICE", "cpu").lower()
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if device not in ("cpu", "cuda"):
        raise ValueError("EVIDENCESEARCH_RESEARCH_DEVICE must be cpu or cuda")
    encoder = SentenceTransformer(MODEL_ID, revision=MODEL_REVISION,
                                  device=device, trust_remote_code=False)
    ce_kwargs: dict[str, Any] = {"max_length": 256, "device": device,
                                  "trust_remote_code": False}
    rev = os.getenv("EVIDENCESEARCH_CE_REVISION", "").strip()
    if rev: ce_kwargs["revision"] = rev
    cross_encoder = CrossEncoder(CE_MODEL_ID, **ce_kwargs)
    return ExpandedEngine(root, encoder=encoder, cross_encoder=cross_encoder)
