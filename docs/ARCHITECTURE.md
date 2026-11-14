# Architecture and data flow

## Request path

1. A user chooses a **domain**, enters or selects a **research question**, and optionally filters by publication year.
2. Next.js sends the request to the FastAPI `/api/research/search` endpoint through its server-side proxy.
3. The backend loads the **local frozen corpus** and validates file and index identities against saved manifests.
4. Field and year filtering constrain eligible documents before ranking.
5. BM25 and MiniLM independently retrieve candidates; **Reciprocal Rank Fusion** combines their rankings (default RRF constant **60**).
6. A pretrained cross-encoder evaluates question–abstract pairs and reranks candidates. Alternative BM25, TF-IDF, dense and hybrid results remain available for comparison.
7. The UI shows ranked documents with source identifiers and bibliographic metadata. An abstract is content retrieved from a local source dataset, **not a verified answer** to the scientific question.

## Components

| Module | Responsibility |
| --- | --- |
| `backend/engine.py` | Frozen SciFact retrieval baseline and benchmark artifacts |
| `backend/expanded_engine.py` | Five-domain corpus and index restoration; lexical / dense / hybrid / reranked search |
| `backend/research_api.py` | Validated `/api/research/*` request handlers |
| `backend/main.py` | FastAPI lifecycle and original SciFact endpoints |
| `web/components/research-explorer.tsx` | Question input, domain selection, filters, results, inspection |
| `web/app/api/research/` | Next.js proxies to the local backend |
| `scripts/smoke_expanded_research.py` | Cross-check API paper titles and abstracts against local source records |

## Frozen baseline settings

- SciFact corpus: **5,183** abstracts; separate SciFact evaluation and frozen model selection.
- Expanded corpus: **5,192** unique papers, five domains.
- MiniLM: `sentence-transformers/multi-qa-MiniLM-L6-cos-v1` (commit `b207367332321f8e44f96e224ef15bc607f4dbf0`).
- Reranker: `cross-encoder/ms-marco-MiniLM-L6-v2`; its checkpoint revision was not pinned in earlier experiments, limiting strict byte-for-byte reranker reproducibility.
- Retrieval: BM25 + MiniLM depth 100, RRF **k=60**, cross-encoder rerank depth 100.

## Current operational scope

This project does **not** currently implement scientific claim verification, citation graph inference, retrieval across the live web, authentication, or a publicly distributable research corpus. Those omissions are deliberate; they avoid claiming an evidence standard the system has not established.
