from qldpcwatch.models import PaperExtraction, paper_extraction_json_schema
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


def _walk_schema_objects(node: object) -> list[dict]:
    out: list[dict] = []
    if not isinstance(node, dict):
        return out
    if isinstance(node.get("properties"), dict):
        out.append(node)
    for key in ("$defs", "definitions", "properties", "patternProperties"):
        child = node.get(key)
        if isinstance(child, dict):
            for value in child.values():
                out.extend(_walk_schema_objects(value))
    items = node.get("items")
    if isinstance(items, dict):
        out.extend(_walk_schema_objects(items))
    elif isinstance(items, list):
        for value in items:
            out.extend(_walk_schema_objects(value))
    for key in ("allOf", "anyOf", "oneOf", "prefixItems"):
        child = node.get(key)
        if isinstance(child, list):
            for value in child:
                out.extend(_walk_schema_objects(value))
    return out


def test_openai_strict_schema_requires_all_properties() -> None:
    schema = paper_extraction_json_schema()
    objects = _walk_schema_objects(schema)
    assert objects
    for obj in objects:
        props = obj.get("properties", {})
        required = obj.get("required", [])
        assert set(required) == set(props.keys())
