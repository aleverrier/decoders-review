# QLDPCWatch Implementation Status

Last updated: 2026-02-21

## Completed

- Created Python package and CLI entrypoint.
- Implemented arXiv API client with conservative rate limiting and retries.
- Implemented SQLite state tracking for papers, versions, and runs.
- Implemented structured extraction schema and validator.
- Implemented OpenAI Responses API extraction with strict JSON schema output.
- Implemented fallback non-hallucinatory extraction when API key is absent.
- Implemented per-paper output writers (`metadata.json`, `extraction.json`, `summary.md`, `bibtex.bib`, `changelog.md`).
- Implemented version snapshots and diff command.
- Implemented local search command.
- Implemented global index and weekly digest generation.
- Implemented static site rebuild output under `/site/`.
- Added GitHub Actions workflow for weekly/manual updates.
- Added unit tests for arXiv parsing, DB state operations, and schema validation.
- Ran formatter/linter/tests successfully (`ruff format`, `ruff check`, `pytest`).
- Ran end-to-end update smoke run and generated 3 paper folders plus indexes/digest/site.
- Updated arXiv retrieval defaults to abstract-targeted (`abs:`) quantum-LDPC decoder queries.
- Added `qldpcwatch update --refresh-fallback` to re-extract existing abstract-only fallback entries.
- Added `qldpcwatch report` to generate cross-paper decoder/error-model/performance/repo reports.
- Ran full-corpus update on 155 papers; artifacts refreshed (`index`, `digest`, `site`, per-paper metadata/changelog).
- Added a fail-fast guard: `--refresh-fallback` now exits unless `OPENAI_API_KEY` is set.

## In Progress

- Routine updates and future paper refresh runs.
- Full-detail corpus re-extraction with PDFs + valid OpenAI key (current corpus remains fallback-only: 155/155).

## Completed (Deployment)

- Initialized git history in small logical commits.
- Created GitHub repository `aleverrier/decoders-review`.
- Connected local `origin` to `git@github.com:aleverrier/decoders-review.git`.
- Pushed `main` and set branch tracking (`main...origin/main`).

## Pending

- Re-run full fallback refresh with a valid OpenAI key loaded in the same shell.
