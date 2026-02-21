from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepoPaths:
    root: Path
    data: Path
    papers: Path
    indexes: Path
    digests: Path
    cache: Path
    cache_pdfs: Path
    cache_text: Path
    site: Path
    db: Path


def resolve_paths(root: Path | None = None) -> RepoPaths:
    repo_root = (root or Path.cwd()).resolve()
    data = repo_root / "data"
    papers = data / "papers"
    indexes = data / "indexes"
    digests = data / "digests"
    cache = repo_root / "cache"
    cache_pdfs = cache / "pdfs"
    cache_text = cache / "text"
    site = repo_root / "site"
    db = data / "state.db"

    for p in [data, papers, indexes, digests, cache, cache_pdfs, cache_text, site]:
        p.mkdir(parents=True, exist_ok=True)

    return RepoPaths(
        root=repo_root,
        data=data,
        papers=papers,
        indexes=indexes,
        digests=digests,
        cache=cache,
        cache_pdfs=cache_pdfs,
        cache_text=cache_text,
        site=site,
        db=db,
    )
