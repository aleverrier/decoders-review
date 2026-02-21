from __future__ import annotations

import csv
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from qldpcwatch.io_utils import read_json

UNKNOWN = "Unknown / not specified"


def _clean(value: str | None) -> str:
    if value is None:
        return UNKNOWN
    text = str(value).strip()
    return text if text else UNKNOWN


def _join(values: list[str]) -> str:
    if not values:
        return UNKNOWN
    cleaned = [str(v).strip() for v in values if str(v).strip()]
    if not cleaned:
        return UNKNOWN
    return "; ".join(dict.fromkeys(cleaned))


def _threshold_summary(thresholds: list[dict]) -> str:
    if not thresholds:
        return UNKNOWN
    parts: list[str] = []
    for t in thresholds:
        level = _clean(t.get("level"))
        noise = _clean(t.get("noise_model"))
        val = t.get("threshold_value")
        units = _clean(t.get("threshold_units"))
        if val is None:
            parts.append(f"{level} | {noise} | threshold=null")
        else:
            if units == UNKNOWN:
                parts.append(f"{level} | {noise} | threshold={val}")
            else:
                parts.append(f"{level} | {noise} | threshold={val} {units}")
    return " ; ".join(parts)


def _collect_codes(extraction: dict) -> list[str]:
    codes: list[str] = []
    for thr in extraction.get("performance_claims", {}).get("thresholds", []):
        codes.extend([str(c) for c in thr.get("code_families", [])])
    for sim in extraction.get("simulations", []):
        codes.extend([str(c) for c in sim.get("codes_tested", [])])
    unique_codes = dict.fromkeys(c.strip() for c in codes if c.strip())
    return list(unique_codes)


def _collect_noise_models(extraction: dict) -> list[str]:
    models: list[str] = []
    for thr in extraction.get("performance_claims", {}).get("thresholds", []):
        models.append(str(thr.get("noise_model", "")).strip())
    for sim in extraction.get("simulations", []):
        models.append(str(sim.get("noise_model", "")).strip())
    unique_models = dict.fromkeys(model for model in models if model)
    return list(unique_models)


def _collect_sim_levels(extraction: dict) -> list[str]:
    levels = [
        str(sim.get("simulation_level", "")).strip() for sim in extraction.get("simulations", [])
    ]
    unique_levels = dict.fromkeys(level for level in levels if level)
    return list(unique_levels)


def _rows_from_papers(papers_root: Path, *, only_relevant: bool) -> list[dict]:
    rows: list[dict] = []
    for paper_dir in sorted(papers_root.glob("*")):
        if not paper_dir.is_dir():
            continue

        metadata_path = paper_dir / "metadata.json"
        extraction_path = paper_dir / "extraction.json"
        if not metadata_path.exists() or not extraction_path.exists():
            continue

        metadata = read_json(metadata_path)
        extraction = read_json(extraction_path)
        relevance = extraction.get("relevance", {}).get("label", "unknown")
        if only_relevant and relevance not in {"relevant", "maybe"}:
            continue

        links = extraction.get("links", {})
        row = {
            "arxiv_id": metadata.get("arxiv_id", ""),
            "arxiv_version": metadata.get("arxiv_version", ""),
            "title": metadata.get("title", ""),
            "relevance": relevance,
            "confidence": extraction.get("relevance", {}).get("confidence", ""),
            "decoder_name": _clean(extraction.get("decoder", {}).get("name")),
            "decoder_family": _clean(extraction.get("decoder", {}).get("decoder_family")),
            "decoder_description": _clean(
                extraction.get("decoder", {}).get("high_level_description", UNKNOWN)
            ),
            "error_models": _join(_collect_noise_models(extraction)),
            "simulation_levels": _join(_collect_sim_levels(extraction)),
            "codes": _join(_collect_codes(extraction)),
            "headline_claims": _join(
                [
                    str(x)
                    for x in extraction.get("performance_claims", {}).get("headline_claims", [])
                ]
            ),
            "thresholds": _threshold_summary(
                extraction.get("performance_claims", {}).get("thresholds", [])
            ),
            "runtime_scaling": _join(
                [
                    str(x)
                    for x in extraction.get("performance_claims", {}).get(
                        "runtime_scaling_claims", []
                    )
                ]
            ),
            "limitations": _join(
                [
                    str(x)
                    for x in extraction.get("performance_claims", {}).get(
                        "limitations_or_caveats", []
                    )
                ]
            ),
            "code_repos": _join([str(x) for x in links.get("code_repo_urls", [])]),
            "abs_url": str(links.get("abs_url", "")),
            "pdf_url": str(links.get("pdf_url", "")),
            "missing_fields": _join([str(x) for x in extraction.get("missing_fields", [])]),
        }
        rows.append(row)

    rows.sort(
        key=lambda r: (
            0 if r["relevance"] == "relevant" else (1 if r["relevance"] == "maybe" else 2),
            -float(r["confidence"] if str(r["confidence"]).strip() else 0.0),
            str(r["arxiv_id"]),
        )
    )
    return rows


def _write_csv(rows: list[dict], out_csv: Path) -> None:
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out_csv.write_text("", encoding="utf-8")
        return

    fields = [
        "arxiv_id",
        "arxiv_version",
        "title",
        "relevance",
        "confidence",
        "decoder_name",
        "decoder_family",
        "decoder_description",
        "error_models",
        "simulation_levels",
        "codes",
        "headline_claims",
        "thresholds",
        "runtime_scaling",
        "limitations",
        "code_repos",
        "abs_url",
        "pdf_url",
        "missing_fields",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_markdown(rows: list[dict], out_md: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()

    rel_counts = Counter([str(r["relevance"]) for r in rows])
    fam_counts = Counter([str(r["decoder_family"]) for r in rows])

    lines: list[str] = []
    lines.append("# QLDPC Decoder Literature Report")
    lines.append("")
    lines.append(f"Generated at: {now}")
    lines.append(f"Papers included: {len(rows)}")
    lines.append("")

    lines.append("## Relevance counts")
    if rel_counts:
        for label, count in rel_counts.most_common():
            lines.append(f"- {label}: {count}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Decoder family counts")
    if fam_counts:
        for family, count in fam_counts.most_common():
            lines.append(f"- {family}: {count}")
    else:
        lines.append("- None")
    lines.append("")

    lines.append("## Per-paper details")
    if not rows:
        lines.append("- None")
    else:
        for row in rows:
            lines.append("")
            lines.append(f"### `{row['arxiv_id']}{row['arxiv_version']}` - {row['title']}")
            lines.append(f"- Relevance: {row['relevance']} (confidence {row['confidence']})")
            lines.append(f"- Decoder: {row['decoder_name']} ({row['decoder_family']})")
            lines.append(f"- Error model(s): {row['error_models']}")
            lines.append(f"- Simulation level(s): {row['simulation_levels']}")
            lines.append(f"- Codes: {row['codes']}")
            lines.append(f"- Performance (headline): {row['headline_claims']}")
            lines.append(f"- Thresholds: {row['thresholds']}")
            lines.append(f"- Runtime scaling: {row['runtime_scaling']}")
            lines.append(f"- Limitations/caveats: {row['limitations']}")
            lines.append(f"- Code repo(s): {row['code_repos']}")
            lines.append(f"- Missing fields: {row['missing_fields']}")
            lines.append(f"- arXiv abs: {row['abs_url']}")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_report(
    papers_root: Path,
    *,
    out_md: Path,
    out_csv: Path,
    only_relevant: bool,
) -> tuple[Path, Path, int]:
    rows = _rows_from_papers(papers_root, only_relevant=only_relevant)
    _write_csv(rows, out_csv)
    _write_markdown(rows, out_md)
    return out_md, out_csv, len(rows)
