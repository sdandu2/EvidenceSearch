# Local setup and asset requirements

This repository contains **code and documentation only**. Live five-domain search requires datasets and caches that are intentionally not committed.

## Requirements

- Windows 11 or another supported Python/Node development environment.
- Python **3.12+** (project development used Windows and Python 3.12; some research notebooks were also executed with newer Python versions).
- Node.js **22+**, npm.
- Local research assets and model downloads. Initial transformer weight downloads may require Internet access.

## Install source dependencies

```powershell
cd C:\path\to\EvidenceSearch
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements_m15.txt
cd .\web
npm ci
npm run typecheck
npm run build
cd ..
```

Commit `web/package-lock.json` when preparing the public repository; CI uses `npm ci` for deterministic installation. Run `npm install` locally if you need to generate the lockfile once.

## Restore private local artifacts

The development workflow produces these records locally:

```text
data/scifact/corpus.jsonl
data/scifact/queries.jsonl
artifacts/embeddings/scifact_multiqa_minilm_l6_cos_v1_seed31.npz
... other frozen SciFact selection / report files ...
data/research/corpus_expanded_PRIVATE.jsonl
data/research/index_cache/<field>/...
data/research/model_cache/expanded_minilm_documents_seed31.npz
reports/experiments/research_corpus_expansion_seed31/expansion_manifest.json
```

Do not copy these to GitHub. Their hashes must match the saved frozen manifests. The current local launcher runs the original SciFact asset audit on startup; that check is intentional. If SciFact artifacts are missing, the launcher will stop. The expanded research engine also checks the expanded corpus and cache identities before loading.

## Start and verify

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start_local.ps1
# In a second terminal after the API is ready:
.\.venv\Scripts\python.exe -u .\scripts\smoke_expanded_research.py
```

- Web: `http://localhost:3000`
- API docs: `http://127.0.0.1:8000/docs`

If a public tester does not possess the private assets, the application cannot return real papers. This limitation should remain plainly stated in the README rather than presenting illustrative examples as live research.
