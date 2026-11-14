"""Fixture-based tests for expanded search. No model downloads or source-paper access."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.expanded_engine import (
    DOMAINS, MODEL_ID, MODEL_REVISION, ExpandedEngine, TOKEN_RE,
    checksum, signature, text_of,
)


class FakeEncoder:
    def encode(self, texts, **kwargs):
        result = np.zeros((len(texts), 384), dtype=np.float32)
        result[:, 0] = 1.0
        return result


class FakeReranker:
    def predict(self, pairs, **kwargs):
        return np.asarray([sum(w in doc.lower() for w in query.lower().split())
                           for query, doc in pairs], dtype=np.float32)


def prepare_fixture(root: Path):
    data = root / "data" / "research"
    data.mkdir(parents=True)
    papers = []
    for d_index, domain in enumerate(DOMAINS):
        for j in range(6):
            papers.append({"paper_id": f"P{d_index}_{j}", "domains": [domain],
                "title": (f"{domain} scientific analysis of pathways {j}"),
                "abstract": f"This research examines {domain} scientific pathways and sample case {j}. " * 7,
                "year": 2010 + j, "authors": "Researcher, Team", "venue": "Fixture Review",
                "url": f"https://example.org/{d_index}/{j}", "doi": f"10.1/test{j}"})
    corpus = data / "corpus_expanded_PRIVATE.jsonl"
    corpus.write_text("".join(json.dumps(p) + "\n" for p in papers), encoding="utf-8")
    corpus_hash = checksum(corpus)
    acq = root / "reports" / "experiments" / "research_corpus_expansion_seed31"
    acq.mkdir(parents=True)
    (acq / "expansion_manifest.json").write_text(json.dumps({"expanded_sha256": corpus_hash,
        "expanded_global_unique": len(papers), "domain_summary": [{"domain": d, "expanded_memberships":6} for d in DOMAINS]}))
    ids = sorted(str(p["paper_id"]) for p in papers)
    by_id = {p["paper_id"]: p for p in papers}
    doc_sig = signature({"sha": corpus_hash, "ids": ids, "model": MODEL_ID,
        "revision": MODEL_REVISION, "text_policy": "title_space_abstract", "norm": True,
        "dtype": "float32"})
    embeddings = np.zeros((len(ids), 384), dtype=np.float32)
    embeddings[:, 0] = 1
    embed_folder = data / "model_cache"
    embed_folder.mkdir()
    np.savez_compressed(embed_folder / "expanded_minilm_documents_seed31.npz",
                        metadata=json.dumps({"signature": doc_sig}), embeddings=embeddings)
    (data / "guided_questions_unjudged.csv").write_text("domain,question_id,question\nNeuroscience,g1,How does neuroscience work?\n")
    for domain in DOMAINS:
        local_ids = [pid for pid in ids if domain in by_id[pid]["domains"]]
        texts = [text_of(by_id[pid]) for pid in local_ids]
        terms = sorted(set(t for text in texts for t in TOKEN_RE.findall(text.lower())))
        word_index = {word: i for i, word in enumerate(terms)}
        tf = np.zeros((len(local_ids), len(terms)), dtype=np.float32)
        lengths = []
        for i, txt in enumerate(texts):
            counts = Counter(TOKEN_RE.findall(txt.lower()))
            lengths.append(sum(counts.values()))
            for word, count in counts.items(): tf[i, word_index[word]] = count
        df = (tf > 0).sum(axis=0)
        idfs = np.log1p((len(local_ids) - df + .5) / (df + .5)).tolist()
        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english",
                              sublinear_tf=True, dtype=np.float32)
        mat = vec.fit_transform(texts)
        folder = data / "index_cache" / domain.lower().replace(" ", "_")
        folder.mkdir(parents=True)
        sparse.save_npz(folder / "bm25_tf_counts.npz", sparse.csr_matrix(tf))
        np.save(folder / "bm25_lengths.npy", np.asarray(lengths, dtype=np.float32))
        sparse.save_npz(folder / "tfidf_matrix.npz", mat)
        (folder / "bm25_lexicon.json").write_text(json.dumps({"terms":terms,"idf":idfs,
                                                           "avgdl": float(np.mean(lengths))}))
        (folder / "tfidf_vectorizer.json").write_text(json.dumps({
            "vocabulary": vec.vocabulary_, "idf": vec.idf_.tolist(),
            "ngram_range": [1, 2], "stop_words": "english", "sublinear_tf": True}))
        sig = signature({"corpus_sha256": corpus_hash,"domain":domain,"ids":local_ids,
                         "bm25":{"k1":1.5,"b":.75},"tfidf":{"ngram_range":[1,2],
                         "stop_words":"english","sublinear_tf":True}})
        (folder / "manifest.json").write_text(json.dumps({"signature":sig,"doc_ids":local_ids}))
    return papers


@pytest.fixture
def engine(tmp_path):
    prepare_fixture(tmp_path)
    return ExpandedEngine(tmp_path, encoder=FakeEncoder(), cross_encoder=FakeReranker(), min_documents=30)


def test_real_snapshot_paths_and_methods(engine):
    result = engine.search(query="neuroscience scientific pathways", domain="Neuroscience", limit=3)
    assert set(result["methods"]) == {"bm25", "tfidf", "dense", "hybrid", "reranked"}
    assert all(len(x) == 3 for x in result["methods"].values())
    assert all(x["source_url"].startswith("https://example.org/") for x in result["methods"]["reranked"])
    assert all(x["title"] == engine.by_id[x["paper_id"]]["title"] for x in result["methods"]["reranked"])
    assert result["filtered_count"] == 6
    assert engine.domains()["fields"][0]["documents"] == 6
    assert engine.domains()["fields"][0]["suggested_questions"]


def test_year_filter_restricts_all_methods(engine):
    result = engine.search(query="neuroscience pathways", domain="Neuroscience", year_min=2014)
    assert result["filtered_count"] == 2
    for entries in result["methods"].values():
        assert len(entries) == 2
        assert all(int(row["year"]) >= 2014 for row in entries)


def test_restored_tfidf_and_bm25_are_deterministic(engine):
    field = engine.fields["Neuroscience"]
    s1 = field.tfidf("scientific pathways")
    s2 = field.tfidf("scientific pathways")
    assert s1.shape == (6,)
    assert np.isfinite(s1).all()
    assert np.allclose(s1, s2)
    assert np.isfinite(field.bm25("neuroscience")).all()


def test_invalid_and_tampered_snapshot(tmp_path, engine):
    with pytest.raises(ValueError):engine.search(query="hello research", domain="unrecognized")
    with pytest.raises(ValueError):engine.search(query="", domain="Neuroscience")
    path = tmp_path / "data/research/corpus_expanded_PRIVATE.jsonl"
    path.write_text(path.read_text() + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="Corpus differs"):
        ExpandedEngine(tmp_path, encoder=FakeEncoder(), cross_encoder=FakeReranker(), min_documents=30)


def test_router_with_fixture_engine(engine, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import backend.research_api as api
    monkeypatch.setattr(api, "_engine", engine)
    monkeypatch.setattr(api, "ROOT", engine.root)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    assert client.get("/api/research/domains").status_code == 200
    resp = client.post("/api/research/search",json={"query":"neuroscience research pathways", "domain":"Neuroscience"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["methods"]["reranked"]
    assert client.post("/api/research/search",json={"query":"xx", "domain":"Neuroscience"}).status_code == 422
