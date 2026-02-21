from __future__ import annotations

import csv
from pathlib import Path

from qldpcwatch.io_utils import read_json, write_json


def rebuild_indexes(papers_root: Path, indexes_root: Path) -> tuple[Path, Path]:
    indexes_root.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []

    for paper_dir in sorted(papers_root.glob("*")):
        if not paper_dir.is_dir():
            continue
        metadata_file = paper_dir / "metadata.json"
        extraction_file = paper_dir / "extraction.json"
        if not metadata_file.exists() or not extraction_file.exists():
            continue

        metadata = read_json(metadata_file)
        extraction = read_json(extraction_file)

        flat = {
            "arxiv_id": metadata.get("arxiv_id"),
            "arxiv_version": metadata.get("arxiv_version"),
            "title": metadata.get("title"),
            "authors": "; ".join(metadata.get("authors", [])),
            "submitted_date": metadata.get("submitted_date"),
            "updated_date": metadata.get("updated_date"),
            "primary_category": metadata.get("primary_category"),
            "categories": "; ".join(metadata.get("categories", [])),
            "relevance": extraction.get("relevance", {}).get("label"),
            "relevance_confidence": extraction.get("relevance", {}).get("confidence"),
            "decoder_family": extraction.get("decoder", {}).get("decoder_family"),
            "decoder_name": extraction.get("decoder", {}).get("name"),
            "missing_fields": "; ".join(extraction.get("missing_fields", [])),
            "paper_dir": str(paper_dir),
        }
        records.append({"metadata": metadata, "extraction": extraction, "flat": flat})

    records.sort(
        key=lambda x: (
            x["metadata"].get("updated_date", ""),
            x["metadata"].get("arxiv_id", ""),
            x["metadata"].get("arxiv_version", ""),
        ),
        reverse=True,
    )

    index_json = [
        {
            **r["metadata"],
            "relevance": r["extraction"].get("relevance", {}),
            "decoder": r["extraction"].get("decoder", {}),
            "links": r["extraction"].get("links", {}),
            "missing_fields": r["extraction"].get("missing_fields", []),
        }
        for r in records
    ]

    index_json_path = indexes_root / "index.json"
    write_json(index_json_path, index_json)

    index_csv_path = indexes_root / "index.csv"
    fieldnames = [
        "arxiv_id",
        "arxiv_version",
        "title",
        "authors",
        "submitted_date",
        "updated_date",
        "primary_category",
        "categories",
        "relevance",
        "relevance_confidence",
        "decoder_family",
        "decoder_name",
        "missing_fields",
        "paper_dir",
    ]
    with index_csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in records:
            writer.writerow(row["flat"])

    return index_json_path, index_csv_path
