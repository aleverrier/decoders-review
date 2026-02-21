from __future__ import annotations

from jsonschema import ValidationError, validate

from qldpcwatch.models import PaperExtraction, paper_extraction_json_schema


def validate_extraction_payload(payload: dict) -> tuple[bool, str | None]:
    schema = paper_extraction_json_schema()
    try:
        validate(instance=payload, schema=schema)
        PaperExtraction.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        return False, str(exc)
    return True, None
