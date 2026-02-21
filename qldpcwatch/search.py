from __future__ import annotations

from pathlib import Path

from qldpcwatch.io_utils import read_json


def search_local(papers_root: Path, query: str, limit: int = 20) -> list[dict]:
    needle = query.lower().strip()
    if not needle:
        return []

    results: list[dict] = []
    for paper_dir in sorted(papers_root.glob("*")):
        if not paper_dir.is_dir():
            continue

        metadata_path = paper_dir / "metadata.json"
        extraction_path = paper_dir / "extraction.json"
        summary_path = paper_dir / "summary.md"
        if not metadata_path.exists():
            continue

        metadata = read_json(metadata_path)
        extraction = read_json(extraction_path) if extraction_path.exists() else {}
        summary = summary_path.read_text(encoding="utf-8") if summary_path.exists() else ""

        haystack = "\n".join(
            [
                str(metadata.get("title", "")),
                " ".join(metadata.get("authors", [])),
                str(metadata.get("abstract", "")),
                str(extraction.get("decoder", {}).get("high_level_description", "")),
                str(extraction.get("relevance", {}).get("rationale", "")),
                summary,
            ]
        ).lower()

        if needle in haystack:
            results.append(
                {
                    "arxiv_id": metadata.get("arxiv_id"),
                    "arxiv_version": metadata.get("arxiv_version"),
                    "title": metadata.get("title"),
                    "relevance": extraction.get("relevance", {}).get("label", "unknown"),
                    "paper_dir": str(paper_dir),
                }
            )

        if len(results) >= limit:
            break

    return results
