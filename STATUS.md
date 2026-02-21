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

## In Progress

- Pushing commits to dedicated GitHub remote (blocked: no git remote configured in this repo).

## Pending

- Configure repository remote if not already set.
