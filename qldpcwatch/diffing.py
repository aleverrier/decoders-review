from __future__ import annotations

import difflib
from pathlib import Path

from qldpcwatch.io_utils import read_json, stable_json_dumps


def _version_num(version: str) -> int:
    try:
        return int(version.removeprefix("v"))
    except ValueError:
        return -1


def diff_latest_two_versions(paper_dir: Path) -> str:
    versions_dir = paper_dir / "versions"
    if not versions_dir.exists():
        return "No versions directory found for this paper."

    version_dirs = [p for p in versions_dir.glob("v*") if p.is_dir()]
    if len(version_dirs) < 2:
        return "Need at least two versions to diff."

    version_dirs.sort(key=lambda p: _version_num(p.name))
    prev_dir = version_dirs[-2]
    curr_dir = version_dirs[-1]

    prev_file = prev_dir / "extraction.json"
    curr_file = curr_dir / "extraction.json"
    if not prev_file.exists() or not curr_file.exists():
        return "Missing extraction snapshots for latest two versions."

    prev = stable_json_dumps(read_json(prev_file)).splitlines(keepends=True)
    curr = stable_json_dumps(read_json(curr_file)).splitlines(keepends=True)

    diff_lines = difflib.unified_diff(
        prev,
        curr,
        fromfile=f"{prev_dir.name}/extraction.json",
        tofile=f"{curr_dir.name}/extraction.json",
        lineterm="",
    )
    text = "\n".join(diff_lines)
    return text if text.strip() else "No differences found between latest two versions."
