import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.engine import RetrievalEngine, fuse_rrf, verified_embeddings
from backend.main import create_app


class FakeEmbedder:
    def encode(self, texts, **kwargs):
        arr = np.zeros((len(texts), 384), dtype=np.float32)
        arr[:, 0] = 1
        return arr


class FakeReranker:
    def predict(self, pairs, **kwargs):
        return np.array([1.0 if 'qubit' in doc.lower() else 0.0 for query, doc in pairs], dtype=np.float32)


def fixture_engine():
    corpus = {
        '1': {'title':'Neural circuit research', 'text':'Synapses connect neurons.'},
        '2': {'title':'Logical qubit protection', 'text':'Quantum error correction protects logical qubits.'},
        '3': {'title':'Immune cell research', 'text':'T cells participate in immune defense.'},
    }
    emb = np.zeros((3,384),dtype=np.float32)
    emb[:,0] = [0.8, 1., 0.3]
    return RetrievalEngine(corpus,emb,FakeEmbedder(),FakeReranker())


def test_rrf_tie_determinism():
    assert [d for d,_ in fuse_rrf(['a','b'], ['b','c'])] == ['b','a','c']


def test_search_real_pipeline_logic_no_fake_results():
    engine=fixture_engine()
    a=engine.search('logical qubit correction',limit=3)
    b=engine.search('logical qubit correction',limit=3)
    assert a['methods']==b['methods']
    assert a['methods']['reranked'][0]['document_id']=='2'
    assert set(a['methods']) == {'bm25','hybrid','reranked'}
    assert all(x['document_id'] in engine.corpus for rows in a['methods'].values() for x in rows)
    assert all(set(x['ranks']) == set(a['methods']) for x in a['traces'])
    # Atlas must be derived from the same real source documents and cached embeddings.
    assert a['atlas'] == b['atlas']
    assert a['atlas']['layout'] == 'miniLM-query-relative-pca'
    assert set(p['document_id'] for p in a['atlas']['points']).issubset(engine.corpus)
    assert all(-0.94 <= p[c] <= 0.94 for p in a['atlas']['points'] for c in ('x','y'))
    assert all(link['source'] in engine.corpus and link['target'] in engine.corpus
               for link in a['atlas']['links'])


def test_api_contract():
    engine=fixture_engine()
    def bench(_): return {'query_count':647,'metrics':{}}
    app=create_app(engine_factory=lambda _: engine, benchmarks_factory=bench,root=Path('.'))
    with TestClient(app) as client:
        assert client.get('/api/health').json()['documents']==3
        assert client.get('/api/benchmarks').json()['query_count']==647
        r=client.post('/api/search',json={'query':'logical qubit correction','limit':2})
        assert r.status_code==200
        assert len(r.json()['methods']['reranked'])==2
        assert client.post('/api/search',json={'query':'  ', 'limit':2}).status_code==422
        assert client.post('/api/search',json={'query':'valid search','limit':21}).status_code==422


def test_embedding_cache_validation(tmp_path):
    corpus = tmp_path/'data'/'scifact'
    corpus.mkdir(parents=True)
    (corpus/'corpus.jsonl').write_text('{}\n',encoding='utf8')
    (corpus/'queries.jsonl').write_text('{}\n',encoding='utf8')
    with pytest.raises(FileNotFoundError):
        verified_embeddings(tmp_path, ['a'])


def test_live_audit_detects_fake_or_changed_source():
    from backend.smoke_live import audit, QUERY
    engine = fixture_engine()
    response = engine.search(QUERY, limit=3)
    # The on-server contract requires ten results, so use a synthetic 10-record fixture.
    corpus = {str(i): {'title': f'Paper {i}', 'text': f'Abstract for document {i}'} for i in range(10)}
    array = np.zeros((10,384),dtype=np.float32)
    array[:,0] = 1
    live = RetrievalEngine(corpus, array, FakeEmbedder(), FakeReranker()).search(QUERY, limit=10)
    live['collection']['document_count'] = 10
    assert audit(live, corpus)['source_text_rows_checked'] == 30
    live['methods']['reranked'][0]['title'] = 'Fictional title'
    with pytest.raises(AssertionError, match='Source text differs'):
        audit(live, corpus)


def test_observatory_provenance_audit():
    from backend.smoke_observatory import audit
    engine = fixture_engine()
    payload = engine.search('logical qubit correction', limit=3)
    assert audit(payload, engine.corpus)['atlas_documents_verified'] == 3
    payload['atlas']['points'][0]['abstract'] = 'Invented text'
    with pytest.raises(AssertionError, match='Atlas abstract differs'):
        audit(payload, engine.corpus)
