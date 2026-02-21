from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from qldpcwatch.arxiv import ArxivClient, filter_since
from qldpcwatch.bibtex import generate_bibtex
from qldpcwatch.config import AppConfig
from qldpcwatch.digest import write_weekly_digest
from qldpcwatch.extraction import ExtractorConfig, OpenAIExtractor
from qldpcwatch.indexer import rebuild_indexes
from qldpcwatch.io_utils import read_json, sha256_text, stable_json_dumps, write_json
from qldpcwatch.models import ArxivPaper, PaperExtraction, PaperMetadata
from qldpcwatch.paths import RepoPaths
from qldpcwatch.pdf_text import (
    download_pdf,
    extract_pdf_text_pages,
    load_text_cache,
    save_text_cache,
    select_relevant_chunks,
    text_pages_hash,
)
from qldpcwatch.repo_layout import paper_dir_from_id
from qldpcwatch.site_builder import rebuild_site
from qldpcwatch.state import StateDB
from qldpcwatch.summary import render_summary_markdown

LOGGER = logging.getLogger(__name__)


def _version_num(version: str) -> int:
    try:
        return int(version.removeprefix("v"))
    except ValueError:
        return -1


@dataclass
class UpdateResult:
    run_at: str
    scanned: int
    processed: int
    new_papers: int
    updated_papers: int
    skipped: int
    digest_path: Path
    index_json_path: Path
    index_csv_path: Path
    site_path: Path | None


def _paper_source_hash(
    paper: ArxivPaper,
    *,
    download_pdfs: bool,
    cache_pdf_path: Path,
    cache_text_path: Path,
    max_text_chars: int,
) -> tuple[str, list[str], bool]:
    if not download_pdfs:
        source_hash = sha256_text(f"{paper.title}\n{paper.abstract}")
        return source_hash, [paper.abstract], False

    if not cache_pdf_path.exists():
        LOGGER.info("Downloading PDF for %s from %s", paper.arxiv_id, paper.pdf_url)
        download_pdf(paper.pdf_url, cache_pdf_path)

    if cache_text_path.exists():
        pages = load_text_cache(cache_text_path)
    else:
        pages = extract_pdf_text_pages(cache_pdf_path)
        save_text_cache(cache_text_path, pages)

    source_hash = text_pages_hash(pages)
    chunks = select_relevant_chunks(
        pages,
        max_chars=max_text_chars,
        keywords=[
            "decoder",
            "decoding",
            "belief propagation",
            "union-find",
            "small-set-flip",
            "threshold",
            "simulation",
        ],
    )
    if not chunks:
        chunks = [paper.abstract]
    return source_hash, chunks, True


def _make_tags(extraction: PaperExtraction) -> list[str]:
    tags: list[str] = []
    tags.extend(extraction.categories)
    tags.append(f"relevance:{extraction.relevance.label}")
    if extraction.decoder.decoder_family:
        tags.append(f"decoder_family:{extraction.decoder.decoder_family}")
    tags.extend(extraction.relevance.matched_keywords)
    return sorted(set(tags))


def _append_changelog(changelog_path: Path, line: str) -> None:
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    if not changelog_path.exists():
        changelog_path.write_text("# Changelog\n\n", encoding="utf-8")
    with changelog_path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def _snapshot_version(
    paper_dir: Path,
    version: str,
    *,
    metadata_path: Path,
    extraction_path: Path,
    summary_path: Path,
    bibtex_path: Path,
) -> None:
    dst = paper_dir / "versions" / version
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(metadata_path, dst / "metadata.json")
    shutil.copy2(extraction_path, dst / "extraction.json")
    shutil.copy2(summary_path, dst / "summary.md")
    shutil.copy2(bibtex_path, dst / "bibtex.bib")


def _reuse_or_extract(
    *,
    paper: ArxivPaper,
    source_hash: str,
    chunks: list[str],
    state: StateDB,
    extractor: OpenAIExtractor,
    paper_dir: Path,
) -> tuple[PaperExtraction, str]:
    prior = state.find_version_by_source_hash(arxiv_id=paper.arxiv_id, source_hash=source_hash)
    if prior is not None and prior.version != paper.arxiv_version:
        prior_path = paper_dir / "versions" / prior.version / "extraction.json"
        if prior_path.exists():
            prior_data = read_json(prior_path)
            prior_data["arxiv_version"] = paper.arxiv_version
            prior_data["updated_date"] = paper.updated_date
            extraction = PaperExtraction.model_validate(prior_data)
            return extraction, f"reused extraction from {prior.version}"

    extraction = extractor.extract(paper, [paper.abstract] + chunks)
    return extraction, "fresh extraction"


def _process_paper(
    *,
    paper: ArxivPaper,
    paths: RepoPaths,
    cfg: AppConfig,
    state: StateDB,
    extractor: OpenAIExtractor,
    download_pdfs: bool,
    refresh_fallback: bool,
) -> tuple[bool, bool, bool, dict]:
    paper_dir = paper_dir_from_id(paths.papers, paper.arxiv_id)
    paper_dir.mkdir(parents=True, exist_ok=True)

    cache_stem = f"{paper.arxiv_id.replace('/', '__')}_{paper.arxiv_version}"
    pdf_cache_path = paths.cache_pdfs / f"{cache_stem}.pdf"
    text_cache_path = paths.cache_text / f"{cache_stem}.json"

    source_hash, chunks, used_pdf = _paper_source_hash(
        paper,
        download_pdfs=download_pdfs,
        cache_pdf_path=pdf_cache_path,
        cache_text_path=text_cache_path,
        max_text_chars=cfg.openai.max_text_chars,
    )

    extraction_path = paper_dir / "extraction.json"
    existing_version = state.get_version(paper.arxiv_id, paper.arxiv_version)
    has_outputs = (paper_dir / "metadata.json").exists() and extraction_path.exists()
    should_force_refresh = False
    if refresh_fallback and extraction_path.exists():
        try:
            current_extraction = read_json(extraction_path)
            rationale = str(current_extraction.get("relevance", {}).get("rationale", ""))
            should_force_refresh = "Fallback extraction from abstract only" in rationale
        except Exception:
            should_force_refresh = False
    if (
        existing_version is not None
        and str(existing_version["source_hash"]) == source_hash
        and has_outputs
        and not should_force_refresh
    ):
        state.upsert_paper(
            arxiv_id=paper.arxiv_id,
            latest_version=paper.arxiv_version,
            latest_source_hash=source_hash,
            title=paper.title,
            primary_category=paper.primary_category,
        )
        return (
            False,
            False,
            False,
            {
                "arxiv_id": paper.arxiv_id,
                "arxiv_version": paper.arxiv_version,
                "title": paper.title,
                "relevance": "unchanged",
            },
        )

    extraction, extraction_mode = _reuse_or_extract(
        paper=paper,
        source_hash=source_hash,
        chunks=chunks,
        state=state,
        extractor=extractor,
        paper_dir=paper_dir,
    )

    extraction_json = extraction.model_dump(mode="json")
    extraction_hash = sha256_text(stable_json_dumps(extraction_json))

    metadata = PaperMetadata(
        arxiv_id=paper.arxiv_id,
        arxiv_version=paper.arxiv_version,
        title=paper.title,
        authors=paper.authors,
        submitted_date=paper.submitted_date,
        updated_date=paper.updated_date,
        categories=paper.categories,
        primary_category=paper.primary_category,
        abstract=paper.abstract,
        links=extraction.links,
        tags=_make_tags(extraction),
        source_hash=source_hash,
        extraction_hash=extraction_hash,
        last_processed_at=datetime.now(tz=UTC).isoformat(),
    )

    metadata_path = paper_dir / "metadata.json"
    extraction_path = paper_dir / "extraction.json"
    summary_path = paper_dir / "summary.md"
    bibtex_path = paper_dir / "bibtex.bib"

    write_json(metadata_path, metadata.model_dump(mode="json"))
    write_json(extraction_path, extraction_json)
    summary_path.write_text(render_summary_markdown(extraction), encoding="utf-8")
    bibtex_path.write_text(generate_bibtex(paper), encoding="utf-8")
    _snapshot_version(
        paper_dir,
        paper.arxiv_version,
        metadata_path=metadata_path,
        extraction_path=extraction_path,
        summary_path=summary_path,
        bibtex_path=bibtex_path,
    )

    prior_paper = state.get_paper(paper.arxiv_id)
    is_new_paper = prior_paper is None
    is_new_version = False
    if prior_paper is not None:
        prev_version = str(prior_paper["latest_version"])
        is_new_version = _version_num(paper.arxiv_version) > _version_num(prev_version)

    state.record_version(
        arxiv_id=paper.arxiv_id,
        version=paper.arxiv_version,
        updated_date=paper.updated_date,
        source_hash=source_hash,
        extraction_hash=extraction_hash,
    )
    state.upsert_paper(
        arxiv_id=paper.arxiv_id,
        latest_version=paper.arxiv_version,
        latest_source_hash=source_hash,
        title=paper.title,
        primary_category=paper.primary_category,
    )

    changelog_line = (
        f"- {datetime.now(tz=UTC).isoformat()}: `{paper.arxiv_id}{paper.arxiv_version}` "
        f"processed ({extraction_mode}; pdf_text={'yes' if used_pdf else 'no'})."
    )
    _append_changelog(paper_dir / "changelog.md", changelog_line)

    return (
        True,
        is_new_paper,
        is_new_version,
        {
            "arxiv_id": paper.arxiv_id,
            "arxiv_version": paper.arxiv_version,
            "title": paper.title,
            "relevance": extraction.relevance.label,
        },
    )


def _merge_latest_versions(papers: list[ArxivPaper]) -> list[ArxivPaper]:
    latest: dict[str, ArxivPaper] = {}
    for paper in papers:
        prev = latest.get(paper.arxiv_id)
        if prev is None:
            latest[paper.arxiv_id] = paper
            continue
        if _version_num(paper.arxiv_version) > _version_num(prev.arxiv_version):
            latest[paper.arxiv_id] = paper
            continue
        if paper.arxiv_version == prev.arxiv_version and paper.updated_date > prev.updated_date:
            latest[paper.arxiv_id] = paper
    return sorted(
        latest.values(),
        key=lambda p: (p.updated_date, p.arxiv_id, _version_num(p.arxiv_version)),
        reverse=True,
    )


def run_update(
    *,
    paths: RepoPaths,
    cfg: AppConfig,
    since: str | None,
    download_pdfs: bool,
    rebuild_site_flag: bool,
    refresh_fallback: bool = False,
) -> UpdateResult:
    state = StateDB(paths.db)
    started_at = datetime.now(tz=UTC)
    since_value = since or state.get_last_run()
    run_id = state.start_run(since_value)

    client = ArxivClient(cfg.arxiv)
    extractor = OpenAIExtractor(
        ExtractorConfig(model=cfg.openai.default_model, max_text_chars=cfg.openai.max_text_chars)
    )

    expressions = [q.expression for q in cfg.queries]
    discovered = client.search_many(expressions, categories=cfg.filters.categories)
    seen_ids = state.list_seen_papers()
    updates = client.fetch_by_ids(seen_ids)

    candidates = _merge_latest_versions(discovered + updates)
    candidates = filter_since(candidates, since_value)

    total = len(candidates)
    LOGGER.info("Found %d candidate papers after merge/filter", total)
    # Best-effort runtime estimate for visibility before a potentially long run.
    min_per_paper = 2.0 if not download_pdfs else 8.0
    max_per_paper = 10.0 if not download_pdfs else 45.0
    lower_bound = int(min_per_paper * total)
    upper_bound = int(max_per_paper * total)
    LOGGER.info(
        "Estimated runtime range: ~%ss to ~%ss for %d candidates (download_pdfs=%s)",
        lower_bound,
        upper_bound,
        total,
        download_pdfs,
    )

    processed = 0
    skipped = 0
    new_items: list[dict] = []
    updated_items: list[dict] = []

    for idx, paper in enumerate(candidates, start=1):
        elapsed = (datetime.now(tz=UTC) - started_at).total_seconds()
        avg = elapsed / idx if idx else 0.0
        remaining = int(avg * (total - idx))
        LOGGER.info(
            "Processing %d/%d: %s%s (elapsed %.1fs, eta ~%ss)",
            idx,
            total,
            paper.arxiv_id,
            paper.arxiv_version,
            elapsed,
            remaining,
        )
        changed, is_new_paper, is_new_version, digest_item = _process_paper(
            paper=paper,
            paths=paths,
            cfg=cfg,
            state=state,
            extractor=extractor,
            download_pdfs=download_pdfs,
            refresh_fallback=refresh_fallback,
        )

        if changed:
            processed += 1
            if is_new_paper:
                new_items.append(digest_item)
            elif is_new_version:
                updated_items.append(digest_item)
        else:
            skipped += 1

    index_json_path, index_csv_path = rebuild_indexes(paths.papers, paths.indexes)

    site_path: Path | None = None
    if rebuild_site_flag or cfg.site.enabled:
        site_path = rebuild_site(index_json_path, paths.site)

    run_at = datetime.now(tz=UTC).isoformat()
    digest_path = write_weekly_digest(
        paths.digests,
        run_at_iso=run_at,
        new_papers=new_items,
        updated_papers=updated_items,
    )

    state.set_last_run(run_at)
    state.finish_run(
        run_id,
        new_papers=len(new_items),
        updated_papers=len(updated_items),
        notes={"candidates": total, "processed": processed, "skipped": skipped},
    )
    state.close()

    return UpdateResult(
        run_at=run_at,
        scanned=total,
        processed=processed,
        new_papers=len(new_items),
        updated_papers=len(updated_items),
        skipped=skipped,
        digest_path=digest_path,
        index_json_path=index_json_path,
        index_csv_path=index_csv_path,
        site_path=site_path,
    )
