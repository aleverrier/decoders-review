from __future__ import annotations

import re

from qldpcwatch.models import ArxivPaper


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", text)[:24] or "paper"


def generate_bibtex(paper: ArxivPaper) -> str:
    year = paper.submitted_date[:4]
    first_author = paper.authors[0].split()[-1] if paper.authors else "unknown"
    key = f"{_slug(first_author)}{year}{paper.arxiv_id.replace('.', '').replace('/', '')}"
    authors = " and ".join(paper.authors) if paper.authors else "Unknown"
    doi_line = f",\n  doi = {{{paper.doi}}}" if paper.doi else ""

    return (
        f"@article{{{key},\n"
        f"  title = {{{paper.title}}},\n"
        f"  author = {{{authors}}},\n"
        f"  journal = {{arXiv preprint arXiv:{paper.arxiv_id}}},\n"
        f"  year = {{{year}}},\n"
        f"  eprint = {{{paper.arxiv_id}}},\n"
        f"  archivePrefix = {{arXiv}},\n"
        f"  primaryClass = {{{paper.primary_category}}}{doi_line}\n"
        f"}}\n"
    )
