# Data sources, privacy, and publication permissions

## Where the data came from

- **SciFact / BEIR:** original benchmark corpus and frozen evaluation artifacts; independently review original dataset terms before redistribution.
- **OpenAlex:** metadata discovery for all five research fields.
- **Europe PMC:** additional bibliographic data for biomedical fields.

The developer's local expanded snapshot contains 5,192 globally unique papers. This public release **does not include those full bibliographic snapshots, abstracts, or any research-derived caches**.

## Why documents are excluded

Access to a paper or its metadata does not automatically grant a license to republish its abstract. `open_access=true` is **not** sufficient evidence of redistribution rights. Source-level terms, record-level rights, author/journal ownership, and the difference between metadata and full-text rights must be checked.

The current rights-review status for expanded abstracts is **not approved**. Until a record-level authorization process is established, do not deploy endpoints that redistribute the saved abstracts to the public Internet.

## Safe public release boundary

**May publish after review:** original application and retrieval source code, API tests with wholly synthetic fixtures, this project's original UI screenshots, architecture diagrams, and aggregate experimental summaries clearly marked with limitations.

**Do not publish:** `data/`, `reports/`, `artifacts/`, `checkpoints/`, `models/`, generated review CSVs, downloaded archives, API tokens, Hugging Face cache directories, local environment files, raw/derived embeddings, or executed notebook outputs.

## Reproducing experiments

Reproduction currently requires acquiring source data under its applicable terms, constructing the local dataset using research notebooks not included in this public-code release, and producing frozen index/cache manifests. The README must not imply that cloning the repository downloads unrestricted copyrighted abstracts.

This is a technical release boundary, not legal advice. Obtain the relevant licenses and source permissions before publicly serving copyrighted content.
