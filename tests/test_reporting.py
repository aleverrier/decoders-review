import json
from pathlib import Path

from qldpcwatch.reporting import generate_report


def _paper_payload(arxiv_id: str, title: str) -> tuple[dict, dict]:
    metadata = {
        "arxiv_id": arxiv_id,
        "arxiv_version": "v1",
        "title": title,
        "authors": ["A. Author"],
        "submitted_date": "2026-01-01",
        "updated_date": "2026-01-02",
        "categories": ["quant-ph"],
        "primary_category": "quant-ph",
        "abstract": "abstract",
        "links": {
            "pdf_url": f"https://arxiv.org/pdf/{arxiv_id}v1.pdf",
            "abs_url": f"https://arxiv.org/abs/{arxiv_id}v1",
            "code_repo_urls": ["https://github.com/example/repo"],
            "doi": None,
        },
        "tags": ["quant-ph"],
        "source_hash": "abc",
        "extraction_hash": "def",
        "last_processed_at": "2026-01-03T00:00:00+00:00",
    }
    extraction = {
        "arxiv_id": arxiv_id,
        "arxiv_version": "v1",
        "title": title,
        "authors": ["A. Author"],
        "submitted_date": "2026-01-01",
        "updated_date": "2026-01-02",
        "categories": ["quant-ph"],
        "primary_category": "quant-ph",
        "abstract": "abstract",
        "relevance": {
            "label": "relevant",
            "confidence": 0.9,
            "rationale": "matched",
            "matched_keywords": ["quantum ldpc", "decoder"],
        },
        "decoder": {
            "name": "Example Decoder",
            "decoder_family": "BP",
            "high_level_description": "belief propagation with tweaks",
            "key_ideas": [],
            "algorithm_outline": [],
            "complexity_claims": [],
            "implementation_notes": [],
        },
        "performance_claims": {
            "headline_claims": ["improved threshold"],
            "thresholds": [
                {
                    "level": "code_capacity",
                    "noise_model": "depolarizing",
                    "threshold_value": 0.05,
                    "threshold_units": "p",
                    "code_families": ["hypergraph product"],
                    "distance_or_blocklength_range": None,
                    "comparisons": [],
                    "evidence": [],
                }
            ],
            "runtime_scaling_claims": ["near-linear"],
            "limitations_or_caveats": ["small-distance regime"],
        },
        "simulations": [
            {
                "simulation_level": "code_capacity",
                "noise_model": "depolarizing",
                "codes_tested": ["hypergraph product"],
                "decoder_settings": [],
                "metrics_reported": [],
                "main_results": ["outperforms baseline"],
                "evidence": [],
            }
        ],
        "links": metadata["links"],
        "missing_fields": [],
    }
    return metadata, extraction


def test_generate_report_outputs(tmp_path: Path) -> None:
    papers = tmp_path / "papers"
    paper_dir = papers / "1234.5678"
    paper_dir.mkdir(parents=True)
    metadata, extraction = _paper_payload("1234.5678", "Decoder paper")
    (paper_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (paper_dir / "extraction.json").write_text(json.dumps(extraction), encoding="utf-8")

    out_md = tmp_path / "report.md"
    out_csv = tmp_path / "report.csv"
    md, csv_path, count = generate_report(
        papers,
        out_md=out_md,
        out_csv=out_csv,
        only_relevant=False,
    )

    assert count == 1
    assert md.exists()
    assert csv_path.exists()

    text = md.read_text(encoding="utf-8")
    assert "Example Decoder" in text
    assert "depolarizing" in text
    assert "https://github.com/example/repo" in text
