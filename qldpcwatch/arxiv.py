from __future__ import annotations

import logging
import re
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from urllib.parse import urlencode

import feedparser
import requests
from dateutil import parser as dateparser
from tenacity import retry, stop_after_attempt, wait_exponential

from qldpcwatch.config import ArxivConfig
from qldpcwatch.models import ArxivPaper

LOGGER = logging.getLogger(__name__)


ARXIV_ID_RE = re.compile(r"(?P<base>.+?)(?P<ver>v\d+)?$")


def parse_arxiv_id_and_version(raw: str) -> tuple[str, str]:
    token = raw.strip().rstrip("/").split("/")[-1]
    match = ARXIV_ID_RE.match(token)
    if match is None:
        raise ValueError(f"Could not parse arXiv id from: {raw}")
    base = match.group("base")
    version = match.group("ver") or "v1"
    return base, version


def build_search_query(expression: str, categories: list[str] | None = None) -> str:
    if not categories:
        return expression
    cat_q = " OR ".join(f"cat:{c}" for c in categories)
    return f"({expression}) AND ({cat_q})"


def _iso_date(raw: str) -> str:
    dt = dateparser.parse(raw)
    if dt is None:
        raise ValueError(f"Could not parse date: {raw}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.date().isoformat()


class ArxivClient:
    def __init__(self, cfg: ArxivConfig):
        self.cfg = cfg
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": cfg.user_agent})
        self._last_request_at = 0.0

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait_for = self.cfg.rate_limit_seconds - elapsed
        if wait_for > 0:
            LOGGER.debug("Sleeping %.2fs to respect arXiv rate limit", wait_for)
            time.sleep(wait_for)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=20), stop=stop_after_attempt(3), reraise=True
    )
    def _get(self, params: dict[str, str | int]) -> requests.Response:
        self._rate_limit()
        response = self.session.get(self.cfg.base_url, params=params, timeout=30)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response

    def _fetch(self, params: dict[str, str | int]) -> list[ArxivPaper]:
        url = f"{self.cfg.base_url}?{urlencode(params)}"
        LOGGER.info("arXiv request: %s", url)
        resp = self._get(params)
        parsed = feedparser.parse(resp.text)
        papers = [self._parse_entry(e) for e in parsed.entries]
        return papers

    @staticmethod
    def _parse_entry(entry: feedparser.FeedParserDict) -> ArxivPaper:
        base_id, version = parse_arxiv_id_and_version(str(entry.id))
        authors = [str(a.name) for a in entry.get("authors", []) if getattr(a, "name", None)]
        categories = [str(t["term"]) for t in entry.get("tags", []) if t.get("term")]
        primary = categories[0] if categories else "unknown"

        pdf_url = ""
        abs_url = str(entry.id)
        for link in entry.get("links", []):
            href = str(link.get("href", ""))
            rel = str(link.get("rel", ""))
            title = str(link.get("title", ""))
            if title == "pdf" or (rel == "related" and href.endswith(".pdf")):
                pdf_url = href
            if rel == "alternate":
                abs_url = href

        if not pdf_url:
            pdf_url = f"https://arxiv.org/pdf/{base_id}{version}.pdf"

        return ArxivPaper(
            arxiv_id=base_id,
            arxiv_version=version,
            entry_id=str(entry.id),
            title=" ".join(str(entry.title).split()),
            authors=authors,
            submitted_date=_iso_date(str(entry.published)),
            updated_date=_iso_date(str(entry.updated)),
            categories=categories,
            primary_category=primary,
            abstract=" ".join(str(entry.summary).split()),
            pdf_url=pdf_url,
            abs_url=abs_url,
            doi=(str(entry.get("arxiv_doi")) if entry.get("arxiv_doi") else None),
        )

    def search_expression(
        self,
        expression: str,
        *,
        categories: list[str] | None,
        max_results: int | None = None,
    ) -> list[ArxivPaper]:
        query = build_search_query(expression, categories)
        params: dict[str, str | int] = {
            "search_query": query,
            "start": 0,
            "max_results": max_results or self.cfg.max_results_per_query,
            "sortBy": "lastUpdatedDate",
            "sortOrder": "descending",
        }
        return self._fetch(params)

    def search_many(
        self, expressions: Iterable[str], *, categories: list[str] | None
    ) -> list[ArxivPaper]:
        merged: dict[tuple[str, str], ArxivPaper] = {}
        for expr in expressions:
            papers = self.search_expression(expr, categories=categories)
            for paper in papers:
                merged[(paper.arxiv_id, paper.arxiv_version)] = paper
        return sorted(
            merged.values(),
            key=lambda p: (p.updated_date, p.arxiv_id, p.arxiv_version),
            reverse=True,
        )

    def fetch_by_ids(self, arxiv_ids: list[str]) -> list[ArxivPaper]:
        if not arxiv_ids:
            return []
        merged: dict[tuple[str, str], ArxivPaper] = {}
        chunk_size = 50
        for i in range(0, len(arxiv_ids), chunk_size):
            chunk = arxiv_ids[i : i + chunk_size]
            params: dict[str, str | int] = {
                "id_list": ",".join(chunk),
                "start": 0,
                "max_results": len(chunk),
            }
            papers = self._fetch(params)
            for paper in papers:
                merged[(paper.arxiv_id, paper.arxiv_version)] = paper
        return sorted(
            merged.values(),
            key=lambda p: (p.updated_date, p.arxiv_id, p.arxiv_version),
            reverse=True,
        )


def filter_since(papers: list[ArxivPaper], since_iso: str | None) -> list[ArxivPaper]:
    if since_iso is None:
        return papers
    since_dt = datetime.fromisoformat(since_iso)
    filtered: list[ArxivPaper] = []
    for p in papers:
        updated_dt = datetime.fromisoformat(f"{p.updated_date}T00:00:00+00:00")
        if updated_dt >= since_dt:
            filtered.append(p)
    return filtered
