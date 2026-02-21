from qldpcwatch.models import PaperExtraction
from qldpcwatch.schema import validate_extraction_payload


def _valid_payload() -> dict:
    return {
        "arxiv_id": "2401.01234",
        "arxiv_version": "v1",
        "title": "Test",
        "authors": ["A. Author"],
        "submitted_date": "2026-01-01",
        "updated_date": "2026-01-02",
        "categories": ["quant-ph"],
        "primary_category": "quant-ph",
        "abstract": "Abstract",
        "relevance": {
            "label": "maybe",
            "confidence": 0.5,
            "rationale": "Insufficient detail",
            "matched_keywords": [],
        },
        "decoder": {
            "name": None,
            "decoder_family": None,
            "high_level_description": "Unknown / not specified",
            "key_ideas": [],
            "algorithm_outline": [],
            "complexity_claims": [],
            "implementation_notes": [],
        },
        "performance_claims": {
            "headline_claims": [],
            "thresholds": [],
            "runtime_scaling_claims": [],
            "limitations_or_caveats": ["Not enough evidence"],
        },
        "simulations": [],
        "links": {
            "pdf_url": "https://arxiv.org/pdf/2401.01234v1.pdf",
            "abs_url": "https://arxiv.org/abs/2401.01234v1",
            "code_repo_urls": [],
            "doi": None,
        },
        "missing_fields": ["decoder.name"],
    }


def test_schema_validation_success() -> None:
    payload = _valid_payload()
    ok, err = validate_extraction_payload(payload)
    assert ok
    assert err is None
    PaperExtraction.model_validate(payload)


def test_schema_validation_failure() -> None:
    payload = _valid_payload()
    payload["relevance"]["confidence"] = 1.5
    ok, err = validate_extraction_payload(payload)
    assert not ok
    assert err
