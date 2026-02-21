from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from qldpcwatch.config import load_config
from qldpcwatch.diffing import diff_latest_two_versions
from qldpcwatch.indexer import rebuild_indexes
from qldpcwatch.paths import resolve_paths
from qldpcwatch.repo_layout import paper_dir_from_id
from qldpcwatch.search import search_local
from qldpcwatch.site_builder import rebuild_site
from qldpcwatch.updater import run_update

app = typer.Typer(help="Track and summarize arXiv papers about decoding quantum LDPC codes.")
console = Console()
DEFAULT_CONFIG_PATH = Path("config.yaml")


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


@app.command()
def update(
    since: str | None = typer.Option(None, help="ISO timestamp. Defaults to last successful run."),
    download_pdfs: bool = typer.Option(
        False,
        "--download-pdfs/--no-download-pdfs",
        help="Download PDFs and extract text for richer extraction.",
    ),
    rebuild_site_flag: bool = typer.Option(
        False,
        "--rebuild-site/--no-rebuild-site",
        help="Regenerate static website output under /site/.",
    ),
    config: Annotated[Path, typer.Option(help="Path to config YAML.")] = DEFAULT_CONFIG_PATH,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs."),
) -> None:
    """Fetch new/updated arXiv papers, extract structured data, and refresh local indexes."""
    _setup_logging(verbose)
    cfg = load_config(config)
    paths = resolve_paths()

    console.print(
        f"Running update with model={cfg.openai.default_model}, "
        f"download_pdfs={download_pdfs}, since={since or 'last_run'}"
    )

    result = run_update(
        paths=paths,
        cfg=cfg,
        since=since,
        download_pdfs=download_pdfs,
        rebuild_site_flag=rebuild_site_flag,
    )

    console.print("Update complete")
    console.print(
        f"scanned={result.scanned} processed={result.processed} "
        f"new={result.new_papers} updated={result.updated_papers} skipped={result.skipped}"
    )
    console.print(f"index.json: {result.index_json_path}")
    console.print(f"index.csv: {result.index_csv_path}")
    console.print(f"digest: {result.digest_path}")
    if result.site_path:
        console.print(f"site: {result.site_path}")


@app.command("rebuild-site")
def rebuild_site_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Rebuild the local static website from current index data."""
    _setup_logging(verbose)
    paths = resolve_paths()
    index_json, _ = rebuild_indexes(paths.papers, paths.indexes)
    site_index = rebuild_site(index_json, paths.site)
    console.print(f"Rebuilt site at {site_index}")


@app.command()
def search(query: str, limit: int = typer.Option(20, min=1, max=200)) -> None:
    """Search local metadata/summaries/extractions."""
    paths = resolve_paths()
    hits = search_local(paths.papers, query, limit=limit)

    if not hits:
        console.print("No matches found.")
        raise typer.Exit(0)

    table = Table(title=f"Search results ({len(hits)})")
    table.add_column("arXiv")
    table.add_column("Relevance")
    table.add_column("Title")
    table.add_column("Folder")
    for h in hits:
        table.add_row(
            f"{h['arxiv_id']}{h['arxiv_version']}",
            str(h.get("relevance", "unknown")),
            str(h.get("title", "")),
            str(h.get("paper_dir", "")),
        )
    console.print(table)


@app.command()
def diff(arxiv_id: str) -> None:
    """Show structured extraction diff between latest two versions of a paper."""
    paths = resolve_paths()
    paper_dir = paper_dir_from_id(paths.papers, arxiv_id)
    if not paper_dir.exists():
        console.print(f"Paper not found: {arxiv_id}")
        raise typer.Exit(1)

    output = diff_latest_two_versions(paper_dir)
    console.print(output)


if __name__ == "__main__":
    app()
