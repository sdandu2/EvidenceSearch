# EvidenceSearch API

Run from the EvidenceSearch project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements_api.txt
.\.venv\Scripts\python.exe -m pytest backend\tests -q
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The server loads the frozen SciFact corpus from `data/scifact/corpus.jsonl`,
Notebook 02 document embeddings from `artifacts/embeddings/`, and the exact
SentenceTransformer and cross-encoder model IDs from Notebooks 02–05.
The models must be available in the active environment or can be fetched
securely on first load. No relevance labels are loaded by the inference engine.
If a file is missing, startup deliberately fails rather than producing fake search results.

- `GET /api/health`
- `GET /api/benchmarks`
- `POST /api/search` (JSON: `{"query": "...", "limit": 10}`)
- `GET /docs` API explorer

Model scores are not probabilities. Cross-encoder weights weren't pinned by
Notebook 04; their exact resolved revision should be recorded in a future
artifact-lock step before public deployment.
