# GitHub release candidate checklist

## Before making a repository public

- [ ] Verify that all application source changes are saved locally, including the **controlled-select React fix**.
- [ ] Confirm `npm run typecheck`, `npm run build`, and fixture-based backend tests pass.
- [ ] Confirm `web/package-lock.json` exists and is committed; `npm ci` is required by CI.
- [ ] Run the real five-domain local smoke test with your private frozen artifacts.
- [ ] **Do not** stage `data/`, `reports/`, `artifacts/`, research-label exports, model weights/caches, downloaded corpora or executed notebooks.
- [ ] Confirm the screenshot does not contain private search queries or accounts; it is a user-provided home UI screenshot.
- [ ] Run `scripts/stage_public_release.ps1` and `scripts/audit_public_release.py` before committing.
- [ ] Inspect `git diff --cached --stat` and `git diff --cached --name-only` before committing.
- [ ] Review source files for user-specific paths and confidential credentials; audit is only one defense.
- [ ] If the repository has **any previous commits**, inspect their history for exposed content. Adding `.gitignore` does **not** remove committed secrets or data from history.
- [ ] Review third-party package/model licenses. Decide on a code license before allowing reuse; this RC does not add one automatically.
- [ ] Create a **private** GitHub repository for initial inspection, then make it public only after explicit review.
- [ ] Do **not** deploy expanded abstract-serving endpoints publicly until paper-level redistribution rights are verified.

## Safe initial staging (Windows PowerShell)

```powershell
cd C:\path\to\EvidenceSearch
git init  # only if this is not already a Git repository
powershell -ExecutionPolicy Bypass -File .\scripts\stage_public_release.ps1
.\.venv\Scripts\python.exe -u .\scripts\audit_public_release.py
git diff --cached --stat
```

The staging helper only stages documented release paths. It does **not** commit or push. Avoid `git add .` for this project.

For an existing repository with a history of private-file commits, use a new clean repository / carefully audited history rewrite; an ignored file can still remain visible in older commits. The audit does not guarantee the complete history is free of secrets.

## First publication

After all checks pass and you have reviewed the staged content:

```powershell
git commit -m "Prepare EvidenceSearch public-code release candidate"
# Create a private remote repository through GitHub UI, then follow its exact remote setup instructions.
# Do not publish while the research abstract rights audit is incomplete.
```

Do not claim that a public-code repository is a hosted working search demo. A live public app is a separate, rights-gated deployment milestone.
