from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Evidence(StrictModel):
    page: int | None
    section: str | None
    quote: str | None


class Threshold(StrictModel):
    level: Literal[
        "code_capacity",
        "phenomenological",
        "circuit_level",
        "other",
        "unknown",
    ]
    noise_model: str
    threshold_value: float | None
    threshold_units: str | None
    code_families: list[str] = Field(default_factory=list)
    distance_or_blocklength_range: str | None
    comparisons: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Relevance(StrictModel):
    label: Literal["relevant", "maybe", "not_relevant"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    matched_keywords: list[str] = Field(default_factory=list)


class Decoder(StrictModel):
    name: str | None
    decoder_family: Literal["BP", "UF", "SSF", "MWPM", "neural", "hybrid", "other"] | None
    high_level_description: str
    key_ideas: list[str] = Field(default_factory=list)
    algorithm_outline: list[str] = Field(default_factory=list)
    complexity_claims: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)


class PerformanceClaims(StrictModel):
    headline_claims: list[str] = Field(default_factory=list)
    thresholds: list[Threshold] = Field(default_factory=list)
    runtime_scaling_claims: list[str] = Field(default_factory=list)
    limitations_or_caveats: list[str] = Field(default_factory=list)


class Simulation(StrictModel):
    simulation_level: Literal[
        "code_capacity",
        "phenomenological",
        "circuit_level",
        "other",
        "unknown",
    ]
    noise_model: str
    codes_tested: list[str] = Field(default_factory=list)
    decoder_settings: list[str] = Field(default_factory=list)
    metrics_reported: list[str] = Field(default_factory=list)
    main_results: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class Links(StrictModel):
    pdf_url: str
    abs_url: str
    code_repo_urls: list[str] = Field(default_factory=list)
    doi: str | None


class PaperExtraction(StrictModel):
    arxiv_id: str
    arxiv_version: str
    title: str
    authors: list[str] = Field(default_factory=list)
    submitted_date: str
    updated_date: str
    categories: list[str] = Field(default_factory=list)
    primary_category: str
    abstract: str
    relevance: Relevance
    decoder: Decoder
    performance_claims: PerformanceClaims
    simulations: list[Simulation] = Field(default_factory=list)
    links: Links
    missing_fields: list[str] = Field(default_factory=list)

    @field_validator("arxiv_version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        if not value.startswith("v"):
            raise ValueError("arxiv_version must start with 'v'")
        return value

    @field_validator("submitted_date", "updated_date")
    @classmethod
    def _validate_date(cls, value: str) -> str:
        datetime.fromisoformat(value)
        return value


class ArxivPaper(StrictModel):
    arxiv_id: str
    arxiv_version: str
    entry_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    submitted_date: str
    updated_date: str
    categories: list[str] = Field(default_factory=list)
    primary_category: str
    abstract: str
    pdf_url: str
    abs_url: str
    doi: str | None


class PaperMetadata(StrictModel):
    arxiv_id: str
    arxiv_version: str
    title: str
    authors: list[str] = Field(default_factory=list)
    submitted_date: str
    updated_date: str
    categories: list[str] = Field(default_factory=list)
    primary_category: str
    abstract: str
    links: Links
    tags: list[str] = Field(default_factory=list)
    source_hash: str
    extraction_hash: str | None
    last_processed_at: str


def paper_extraction_json_schema() -> dict:
    schema = PaperExtraction.model_json_schema()
    schema["title"] = "PaperExtraction"
    return schema
