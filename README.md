# qldpcwatch

`qldpcwatch` maintains a local, version-aware repository of arXiv papers related to decoding quantum LDPC codes.

## Features

- Periodic arXiv polling with conservative rate limiting (single worker, >=3s between requests).
- Per-paper folder outputs:
  - `metadata.json`
  - `extraction.json` (schema-validated structured extraction)
  - `summary.md`
  - `bibtex.bib`
  - `changelog.md`
  - version snapshots under `versions/vN/`
- Global indexes:
  - `data/indexes/index.json`
  - `data/indexes/index.csv`
  - weekly digest `data/digests/YYYY-WW.md`
- CLI:
  - `qldpcwatch update [--since ...] [--download-pdfs] [--rebuild-site]`
  - `qldpcwatch rebuild-site`
  - `qldpcwatch search "<query>"`
  - `qldpcwatch diff <arxiv_id>`
  - `qldpcwatch report [--only-relevant]`
- Optional static website output in `/site/`.

## Repository Layout

```text
repo_root/
  qldpcwatch/
  scripts/
  data/
    papers/
      <arxiv_id>/
        metadata.json
        extraction.json
        summary.md
        bibtex.bib
        changelog.md
        versions/
    indexes/
      index.json
      index.csv
    digests/
  cache/
    pdfs/
    text/
  site/
  .github/workflows/update.yml
  config.yaml
```

## Local Setup

### 1) Python

Use Python 3.11+.

### 2) Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 3) Configure environment

```bash
export OPENAI_API_KEY="..."
export OPENAI_MODEL="gpt-5"   # optional override
```

If `OPENAI_API_KEY` is not set, update still runs with conservative fallback extraction from metadata/abstract only.

### 4) Configure search strategy

Edit `config.yaml`:

- `queries`: list of arXiv query expressions. Default strategy is abstract-first (`abs:`), with
  `quantum ldpc` + decoder terms for higher-recall corpus collection.
- `filters.categories`: default category allowlist (`quant-ph`, `cs.IT`, `math.IT`, optional `cs.DS`).
- `arxiv.rate_limit_seconds`: keep `>= 3.0`.

## Usage

### Manual update

```bash
qldpcwatch update --download-pdfs --rebuild-site
```

To refresh existing abstract-only fallback entries with full extraction:

```bash
qldpcwatch update --since 2000-01-01T00:00:00+00:00 --download-pdfs --refresh-fallback --rebuild-site
```

Or incremental:

```bash
qldpcwatch update --since 2026-02-01T00:00:00+00:00
```

### Rebuild site only

```bash
qldpcwatch rebuild-site
```

### Search local repository

```bash
qldpcwatch search "belief propagation hypergraph product"
```

### Diff latest two versions

```bash
qldpcwatch diff 2401.01234
```

### Generate a global decoder report

```bash
qldpcwatch report --all-papers
```

Outputs:
- `data/reports/decoder_report.md`
- `data/reports/decoder_report.csv`

## GitHub Actions

Workflow: `.github/workflows/update.yml`

- Triggers weekly (`cron`) and manual (`workflow_dispatch`).
- Installs dependencies.
- Runs:

```bash
qldpcwatch update --rebuild-site
```

- Commits `data/` and `site/` changes back to the repository.

### Required secrets/variables

- `OPENAI_API_KEY` (repository secret)
- optional `OPENAI_MODEL` (repository variable)

## GitHub Pages (optional)

If you want to serve `/site/`:

1. Enable Pages in repository settings.
2. Set source to GitHub Actions or branch/folder as preferred.
3. Publish generated `site/` artifacts.

## Testing, Linting, Formatting

```bash
ruff check .
ruff format .
pytest
```

## Idempotency and Caching

- State is persisted in `data/state.db`.
- If source hash for a paper version is unchanged, extraction is skipped.
- If a new version has the same source hash as a prior version, extraction is reused.

## Structured Extraction Guarantees

- `extraction.json` is validated against the `PaperExtraction` JSON schema.
- No hallucinated fields by design:
  - missing/unknown values remain `null` or empty
  - unresolved items are listed in `missing_fields`

## Known Limitations

- arXiv query recall is heuristic; manual review is still recommended.
- PDF parsing quality depends on document structure.
- Fallback extraction (no API key) is abstract-level and intentionally conservative.

## Manual Overrides

When needed, edit the paper folder directly:

- `data/papers/<arxiv_id>/metadata.json`
- `data/papers/<arxiv_id>/extraction.json`
- `data/papers/<arxiv_id>/summary.md`

Then run:

```bash
qldpcwatch rebuild-site
```

to refresh derived outputs.
