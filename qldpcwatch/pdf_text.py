from __future__ import annotations

import json
import logging
from pathlib import Path

import fitz
import requests

from qldpcwatch.io_utils import sha256_file, sha256_text

LOGGER = logging.getLogger(__name__)


def download_pdf(pdf_url: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(pdf_url, timeout=60, stream=True) as response:
        response.raise_for_status()
        with out_path.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)
    return out_path


def extract_pdf_text_pages(pdf_path: Path) -> list[dict[str, str | int]]:
    doc = fitz.open(pdf_path)
    pages: list[dict[str, str | int]] = []
    for page_index in range(doc.page_count):
        page = doc.load_page(page_index)
        text = page.get_text("text")
        pages.append({"page": page_index + 1, "text": text})
    doc.close()
    return pages


def save_text_cache(cache_path: Path, pages: list[dict[str, str | int]]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")


def load_text_cache(cache_path: Path) -> list[dict[str, str | int]]:
    return json.loads(cache_path.read_text(encoding="utf-8"))


def text_pages_hash(pages: list[dict[str, str | int]]) -> str:
    flattened = "\n".join(str(p["text"]) for p in pages)
    return sha256_text(flattened)


def pdf_hash(pdf_path: Path) -> str:
    return sha256_file(pdf_path)


def select_relevant_chunks(
    pages: list[dict[str, str | int]], *, max_chars: int, keywords: list[str] | None = None
) -> list[str]:
    if not pages:
        return []

    lowered_keywords = [k.lower() for k in (keywords or [])]
    hits: list[str] = []
    fallback: list[str] = []

    for page in pages:
        text = str(page.get("text", "")).strip()
        if not text:
            continue
        compact = " ".join(text.split())
        prefix = f"[page {page['page']}] "
        line = prefix + compact
        if lowered_keywords and any(k in compact.lower() for k in lowered_keywords):
            hits.append(line)
        else:
            fallback.append(line)

    selected: list[str] = []
    total = 0
    for bucket in (hits, fallback):
        for line in bucket:
            if total + len(line) > max_chars:
                return selected
            selected.append(line)
            total += len(line)

    return selected
