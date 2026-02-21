from __future__ import annotations

from pathlib import Path


def paper_dir_name(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "__")


def paper_dir_from_id(papers_root: Path, arxiv_id: str) -> Path:
    return papers_root / paper_dir_name(arxiv_id)
