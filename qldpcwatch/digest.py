from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def current_week_slug(now: datetime | None = None) -> str:
    dt = now or datetime.now(tz=UTC)
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def write_weekly_digest(
    digests_root: Path,
    *,
    run_at_iso: str,
    new_papers: list[dict],
    updated_papers: list[dict],
) -> Path:
    digests_root.mkdir(parents=True, exist_ok=True)
    week = current_week_slug(datetime.fromisoformat(run_at_iso))
    digest_path = digests_root / f"{week}.md"

    lines: list[str] = []
    lines.append(f"# QLDPC Watch Digest {week}")
    lines.append("")
    lines.append(f"Generated at: {run_at_iso}")
    lines.append("")

    lines.append(f"## New papers ({len(new_papers)})")
    if new_papers:
        for p in new_papers:
            item = (
                f"- `{p['arxiv_id']}{p['arxiv_version']}`: "
                f"{p['title']} ({p.get('relevance', 'unknown')})"
            )
            lines.append(item)
    else:
        lines.append("- None")

    lines.append("")
    lines.append(f"## Updated papers ({len(updated_papers)})")
    if updated_papers:
        for p in updated_papers:
            item = (
                f"- `{p['arxiv_id']}{p['arxiv_version']}`: "
                f"{p['title']} ({p.get('relevance', 'unknown')})"
            )
            lines.append(item)
    else:
        lines.append("- None")

    lines.append("")
    digest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return digest_path
