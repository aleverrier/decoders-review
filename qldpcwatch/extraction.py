from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from jsonschema import ValidationError, validate
from openai import OpenAI

from qldpcwatch.models import ArxivPaper, PaperExtraction, paper_extraction_json_schema

LOGGER = logging.getLogger(__name__)


KEYWORDS = [
    "quantum ldpc",
    "decoder",
    "decoding",
    "belief propagation",
    "small-set-flip",
    "union-find",
    "mwpm",
    "hypergraph product",
    "balanced product",
    "lifted product",
]


@dataclass
class ExtractorConfig:
    model: str
    max_text_chars: int


class ExtractionError(RuntimeError):
    pass


def _missing_fields_template() -> list[str]:
    return [
        "decoder.name",
        "decoder.algorithm_outline",
        "decoder.complexity_claims",
        "performance_claims.thresholds",
        "performance_claims.runtime_scaling_claims",
        "simulations",
        "links.code_repo_urls",
    ]


def heuristic_extraction(paper: ArxivPaper) -> PaperExtraction:
    abstract_l = paper.abstract.lower()
    matched = [k for k in KEYWORDS if k in abstract_l]
    label = "relevant" if "quantum ldpc" in abstract_l and ("decod" in abstract_l) else "maybe"

    return PaperExtraction(
        arxiv_id=paper.arxiv_id,
        arxiv_version=paper.arxiv_version,
        title=paper.title,
        authors=paper.authors,
        submitted_date=paper.submitted_date,
        updated_date=paper.updated_date,
        categories=paper.categories,
        primary_category=paper.primary_category,
        abstract=paper.abstract,
        relevance={
            "label": label,
            "confidence": 0.35 if label == "maybe" else 0.55,
            "rationale": "Fallback extraction from abstract only (OpenAI key unavailable).",
            "matched_keywords": matched,
        },
        decoder={
            "name": None,
            "decoder_family": None,
            "high_level_description": "Unknown / not specified from available text.",
            "key_ideas": [],
            "algorithm_outline": [],
            "complexity_claims": [],
            "implementation_notes": [],
        },
        performance_claims={
            "headline_claims": [],
            "thresholds": [],
            "runtime_scaling_claims": [],
            "limitations_or_caveats": [
                "Full paper text not analyzed; extraction limited to metadata/abstract."
            ],
        },
        simulations=[],
        links={
            "pdf_url": paper.pdf_url,
            "abs_url": paper.abs_url,
            "code_repo_urls": [],
            "doi": paper.doi,
        },
        missing_fields=_missing_fields_template(),
    )


class OpenAIExtractor:
    def __init__(self, cfg: ExtractorConfig):
        self.cfg = cfg
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    @staticmethod
    def _response_text(response: object) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return str(output_text)

        output = getattr(response, "output", [])
        chunks: list[str] = []
        for item in output:
            for content in getattr(item, "content", []):
                txt = getattr(content, "text", None)
                if txt:
                    chunks.append(str(txt))
        if chunks:
            return "\n".join(chunks)

        raise ExtractionError("OpenAI response did not include textual output")

    def extract(self, paper: ArxivPaper, chunks: list[str]) -> PaperExtraction:
        if self.client is None:
            LOGGER.warning(
                "OPENAI_API_KEY not set; using fallback extraction for %s", paper.arxiv_id
            )
            return heuristic_extraction(paper)

        text_blob = "\n\n".join(chunks)
        if len(text_blob) > self.cfg.max_text_chars:
            text_blob = text_blob[: self.cfg.max_text_chars]

        system_prompt = (
            "You are an information extraction system for quantum LDPC decoding papers. "
            "Use only the provided abstract and text chunks. Never hallucinate. "
            "If data is missing or ambiguous, set null/empty values and list "
            "missing fields explicitly. "
            "Any numeric threshold/performance claim must include evidence "
            "with page/section/quote when available."
        )

        user_prompt = (
            f"Paper metadata:\n"
            f"arXiv ID: {paper.arxiv_id}\n"
            f"Version: {paper.arxiv_version}\n"
            f"Title: {paper.title}\n"
            f"Authors: {', '.join(paper.authors)}\n"
            f"Submitted date: {paper.submitted_date}\n"
            f"Updated date: {paper.updated_date}\n"
            f"Categories: {', '.join(paper.categories)}\n"
            f"Primary category: {paper.primary_category}\n"
            f"PDF URL: {paper.pdf_url}\n"
            f"Abstract:\n{paper.abstract}\n\n"
            "Extracted text chunks:\n"
            f"{text_blob}\n"
        )

        schema = paper_extraction_json_schema()
        response = self.client.responses.create(
            model=self.cfg.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "PaperExtraction",
                    "strict": True,
                    "schema": schema,
                }
            },
        )

        payload = self._response_text(response)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"Model output was not JSON: {exc}") from exc

        try:
            validate(instance=data, schema=schema)
        except ValidationError as exc:
            raise ExtractionError(f"Model JSON failed schema validation: {exc.message}") from exc

        return PaperExtraction.model_validate(data)
